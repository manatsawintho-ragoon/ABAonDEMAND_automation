"""
MSLearnUnitRunner — completes individual MS Learn units.

Module index page:
  Unit links appear as absolute paths /en-us/training/modules/MODULE/unit-slug/
  or as relative slugs inside the main unit list.

Unit page:
  Just navigating to a unit page marks it complete server-side (when logged in).

Knowledge check page:
  - Q group: [role="radiogroup"] — aria-label contains the question text
  - Options: input[type="radio"] inside each radiogroup
  - Submit:  button matching /submit.?answers/i
  After submit:
  - Correct option: has a leaf element whose text matches /^correct/i
  - Score banner:   text "Score: N%" appears
  - Pass banner:    text "Module assessment passed" appears  ← ms_confirmed
  - NO retry button — re-navigate to the same URL to retry

Caching strategy (reliable, no poisoning):
  - Track what was selected each attempt
  - After submit: scan ALL options for the "Correct" indicator → cache that answer directly
  - If no per-question indicator: cache everything when score == 100%
  - On failure AND cache was used → clear module cache (cached answers were wrong)
  - Add selected answer per question to 'tried' on failure to force different picks next retry

ms_confirmed:
  Set to True only when the page explicitly shows "Module assessment passed".
  This is tracked in progress.json so the engine can re-run modules that were
  marked complete but never got the MS Learn profile badge.
"""

import asyncio
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from playwright.async_api import Page, TimeoutError as PwTimeout

from core.browser import BrowserSession
from utils.llm_answerer import answer_question

# ── JavaScript helpers ────────────────────────────────────────────────────────

_JS_GET_UNIT_LINKS = """
() => {
    const pageUrl = window.location.href;
    const base = pageUrl.replace(/\\/$/, '');
    const origin = 'https://learn.microsoft.com';
    const modulePath = new URL(base).pathname.replace(/\\/$/, '');

    const seen = new Set();
    const links = [];

    document.querySelectorAll('a[href]').forEach(a => {
        const href = a.getAttribute('href');
        if (!href || !href.trim() || href.startsWith('#') || href.startsWith('mailto')) return;

        let unitPath;
        if (!href.startsWith('/') && !href.startsWith('http')) {
            unitPath = modulePath + '/' + href.trim().replace(/^\\//, '');
        } else {
            let path;
            try { path = href.startsWith('http') ? new URL(href).pathname : href; }
            catch(e) { return; }
            path = path.replace(/\\/$/, '');
            if (!path.startsWith(modulePath + '/')) return;
            const suffix = path.slice(modulePath.length + 1);
            if (!suffix || suffix.includes('/')) return;
            unitPath = path;
        }

        const full = origin + unitPath;
        if (!seen.has(full)) { seen.add(full); links.push(full); }
    });
    return links;
}
"""

_JS_IS_KNOWLEDGE_CHECK = """
() => !!document.querySelector('[role="radiogroup"]')
"""

_JS_IS_SUBMITTED = """
() => {
    const radios = document.querySelectorAll('[role="radiogroup"] input[type="radio"]');
    return radios.length > 0 && Array.from(radios).every(r => r.disabled);
}
"""

# Get questions + options.
# Question text priority: aria-label on rg → aria-labelledby → previous sibling → first-p fallback
# Option text: first <p> or <code> inside the option's label/container (skipping question-level p)
_JS_GET_QUESTIONS = """
() => {
    return Array.from(document.querySelectorAll('[role="radiogroup"]')).map((rg, qi) => {
        // --- Question text ---
        let text = '';

        // 1. aria-label directly on the radiogroup (MS Learn often puts full question here)
        const ariaLabel = rg.getAttribute('aria-label');
        if (ariaLabel && ariaLabel.trim().length > 5) {
            text = ariaLabel.trim();
        }

        // 2. aria-labelledby → find the labeled element
        if (!text) {
            const lid = rg.getAttribute('aria-labelledby');
            if (lid) {
                // may be multiple IDs separated by spaces
                for (const id of lid.split(' ')) {
                    const el = document.getElementById(id.trim());
                    if (el) { text = el.innerText.trim(); break; }
                }
            }
        }

        // 3. Previous sibling element (question lives before the radiogroup in the DOM)
        if (!text) {
            let prev = rg.previousElementSibling;
            while (prev) {
                const t = prev.innerText.trim();
                // Must be long enough to be a real question, not a label/button
                if (t.length > 15 && !prev.matches('button, input, [role="radiogroup"]')) {
                    text = t; break;
                }
                prev = prev.previousElementSibling;
            }
        }

        // 4. Parent's first non-rg text element
        if (!text) {
            const parent = rg.parentElement;
            if (parent) {
                for (const el of parent.querySelectorAll('p, h2, h3, h4, legend')) {
                    if (!rg.contains(el) && el.innerText.trim().length > 15) {
                        text = el.innerText.trim(); break;
                    }
                }
            }
        }

        // Strip leading question number "1. "
        text = text.replace(/^\\d+\\.\\s*/, '').trim();

        // --- Options ---
        const inputs = Array.from(rg.querySelectorAll('input[type="radio"]'));
        const options = inputs.map((inp, oi) => {
            // Walk up to find the option container (label or li or div with the option text)
            let container = inp.parentElement;
            // Try to find <p> or <code> that is NOT the question text
            // by looking inside the container only (not the whole rg)
            const textEl = container.querySelector('p, code');
            let optText = textEl ? textEl.innerText.trim() : '';
            // Fallback to label text
            if (!optText) {
                const lbl = rg.querySelector(`label[for="${inp.id}"]`);
                if (lbl) optText = lbl.innerText.trim();
            }
            // Last resort: input value
            if (!optText) optText = inp.value || '';
            return { oi, text: optText };
        });

        return { qi, text, options };
    });
}
"""

_JS_CLICK_RADIO = """
([qi, oi]) => {
    const rgs = document.querySelectorAll('[role="radiogroup"]');
    const rg = rgs[qi];
    if (!rg) return false;
    const inputs = rg.querySelectorAll('input[type="radio"]');
    const inp = inputs[oi];
    if (!inp) return false;
    inp.click();
    return true;
}
"""

_JS_SUBMIT = """
() => {
    for (const btn of document.querySelectorAll('button')) {
        if (/submit.?answers/i.test(btn.innerText.trim())) {
            btn.click(); return true;
        }
    }
    return false;
}
"""

# Parse results after submit.
# For EACH radiogroup:
#   selectedText: text of the option the user chose (inp.checked)
#   correctText:  text of the option that has a "Correct" indicator (ANY option, not just selected)
#   isCorrect:    selectedText == correctText
#
# This approach works whether or not the correct indicator is on the selected option.
_JS_GET_RESULTS = """
() => {
    return Array.from(document.querySelectorAll('[role="radiogroup"]')).map((rg, qi) => {
        let selectedText = '';
        let correctText  = '';

        rg.querySelectorAll('input[type="radio"]').forEach(inp => {
            const container = inp.parentElement;
            const textEl    = container.querySelector('p, code');
            const optText   = textEl ? textEl.innerText.trim() : (inp.value || '');

            if (inp.checked) selectedText = optText;

            // Check every descendant of this option's container for a "Correct" indicator
            const isMarkedCorrect = (
                // Text "Correct" or "Correct!" anywhere in the option container
                Array.from(container.querySelectorAll('*')).some(el =>
                    el.childElementCount === 0 &&
                    /^correct[!.]?$/i.test(el.innerText.trim())
                ) ||
                // CSS class containing 'correct' on the container or a child
                container.classList.contains('is-correct') ||
                Array.from(container.querySelectorAll('[class*="correct"]')).length > 0 ||
                // aria-label or data attribute
                container.getAttribute('aria-label') === 'Correct' ||
                container.querySelector('[aria-label="Correct"]') !== null
            );

            if (isMarkedCorrect && optText) correctText = optText;
        });

        const isCorrect = !!(selectedText && correctText && selectedText === correctText);
        return { qi, selectedText, correctText, isCorrect };
    });
}
"""

_JS_GET_SCORE = """
() => {
    const body = document.body.innerText || '';
    // "Module assessment passed" is the definitive pass signal → treat as 100
    if (/module assessment passed/i.test(body)) return 100;
    // Try common score formats in order of specificity
    const patterns = [
        /Score[:\\s]+(\\d+)%/i,
        /You scored[:\\s]+(\\d+)%/i,
        /(\\d+)%\\s*(correct|score)/i,
        /(\\d+)%/,
    ];
    for (const p of patterns) {
        const m = body.match(p);
        if (m) return parseInt(m[1]);
    }
    return null;
}
"""

# Definitive check: did MS Learn explicitly confirm the assessment is passed?
_JS_MS_CONFIRMED = """
() => /module assessment passed/i.test(document.body.innerText || '')
"""

_JS_GET_NEXT_URL = """
() => {
    for (const a of document.querySelectorAll('a[href]')) {
        if (a.innerText.trim() === 'Next') return a.href;
    }
    return null;
}
"""

_JS_IS_LAST_UNIT = """
() => !Array.from(document.querySelectorAll('a')).some(a => a.innerText.trim() === 'Next')
"""


def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


class MSLearnUnitRunner:
    """Completes all units in a MS Learn module."""

    def __init__(self,
                 session: BrowserSession,
                 on_log: Callable[[str, int], None],
                 stop_flag: Callable[[], bool],
                 answer_cache: Dict[str, Dict[str, Any]],
                 max_retry: int = 3,
                 api_key: str = "",
                 ai_model: str = ""):
        self._s       = session
        self._log     = on_log
        self._running = stop_flag
        self._cache   = answer_cache   # {module_id: {q_text: correct_opt_text}}
        self._max_retry = max_retry
        self._api_key = api_key
        self._ai_model = ai_model

    # ── Public entry point ────────────────────────────────────────────────────

    async def complete_module(self, page: Page,
                              module_url: str, module_id: str,
                              ep_idx: int,
                              module_title: str = "") -> Tuple[bool, int, bool]:
        """Navigate through all units in module.
        Returns (passed, score%, ms_confirmed).
        ms_confirmed=True only when MS Learn showed 'Module assessment passed'.
        """
        self._log(f"  [module] กำลังค้นหา units…", ep_idx)
        await self._s.navigate(page, module_url)
        await self._s.delay(1.5)

        unit_links: List[str] = await page.evaluate(_JS_GET_UNIT_LINKS)
        self._log(f"  [module] พบ {len(unit_links)} units", ep_idx)

        if not unit_links:
            self._log(f"  [module] ไม่พบ units — ข้าม", ep_idx)
            return False, 0, False

        n_done = 0
        quiz_score = 0
        quiz_passed = False
        module_ms_confirmed = False

        for u_idx, unit_url in enumerate(unit_links):
            if not self._running():
                break

            slug = unit_url.rstrip('/').rsplit('/', 1)[-1]
            self._log(f"  [unit {u_idx+1}/{len(unit_links)}] {slug}", ep_idx)

            try:
                await self._s.navigate(page, unit_url)
                await self._s.delay(1.0)

                if await page.evaluate(_JS_IS_KNOWLEDGE_CHECK):
                    self._log(f"  [unit] knowledge check ตรวจพบ", ep_idx)
                    quiz_score, quiz_passed, quiz_confirmed = await self._do_knowledge_check(
                        page, unit_url, module_id, ep_idx, module_title)
                    if quiz_confirmed:
                        module_ms_confirmed = True
                else:
                    await self._do_regular_unit(page, ep_idx)

                n_done += 1

            except Exception as e:
                self._log(f"  [unit {u_idx+1}] error: {e}", ep_idx)

        total = len(unit_links)
        if quiz_passed:
            return True, 100, module_ms_confirmed
        if n_done == total and total > 0:
            return True, 100, module_ms_confirmed
        score_pct = round(n_done / total * 100) if total else 0
        return score_pct >= 100, score_pct, module_ms_confirmed

    # ── Regular unit ──────────────────────────────────────────────────────────

    async def _do_regular_unit(self, page: Page, ep_idx: int) -> None:
        is_last = await page.evaluate(_JS_IS_LAST_UNIT)
        if is_last:
            self._log(f"  [unit] last unit — complete", ep_idx)

    # ── Knowledge check ───────────────────────────────────────────────────────

    async def _do_knowledge_check(self, page: Page, unit_url: str,
                                  module_id: str, ep_idx: int,
                                  module_title: str = "") -> Tuple[int, bool, bool]:
        """Answer knowledge check. Returns (score%, passed, ms_confirmed)."""
        mod_cache = self._cache.setdefault(module_id, {})

        # tried[q_text] = set of option texts already tried and known wrong
        tried: Dict[str, Set[str]] = {}
        score = 0

        for attempt in range(1, self._max_retry + 1):
            if not self._running():
                return 0, False, False

            # Reload if previously submitted (radios are disabled)
            if await page.evaluate(_JS_IS_SUBMITTED):
                await self._s.navigate(page, unit_url)
                await self._s.delay(1.0)

            self._log(f"  [quiz] attempt {attempt}/{self._max_retry}", ep_idx)

            questions = await page.evaluate(_JS_GET_QUESTIONS)
            if not questions:
                self._log(f"  [quiz] ไม่พบ questions", ep_idx)
                return 0, False, False

            # Track what we select this attempt: {q_text: selected_option_text}
            selected_this_attempt: Dict[str, str] = {}
            used_cache_questions: Set[str] = set()

            for q in questions:
                q_text = _clean(q['text'])
                opts   = [_clean(o['text']) for o in q['options']]
                qi     = q['qi']

                if not q_text or not opts:
                    continue

                pick: Optional[str] = None

                # 1. Cache hit — known correct answer
                cached = mod_cache.get(q_text)
                if cached and cached in opts:
                    pick = cached
                    used_cache_questions.add(q_text)
                    self._log(f"    Q{qi+1}: cache  [{opts.index(pick)}] {pick[:45]!r}", ep_idx)

                if pick is None:
                    # 2. Eliminate options already known wrong
                    q_tried = tried.get(q_text, set())
                    untried = [t for t in opts if t not in q_tried]

                    # Elimination converged → only one option left
                    if len(untried) == 1:
                        pick = untried[0]
                        self._log(f"    Q{qi+1}: elim   [{opts.index(pick)}] {pick[:45]!r}", ep_idx)

                if pick is None:
                    # 3. AI — pass "tried" answers as hints so it avoids them on retries
                    candidates  = untried if untried else opts
                    q_tried_str = ", ".join(f'"{t}"' for t in tried.get(q_text, set()))
                    hint = (f"Previously tried and wrong: {q_tried_str}. "
                            f"Choose a DIFFERENT answer." if q_tried_str else "")
                    ai_question = f"{question_with_hint(q_text, hint)}"

                    llm_idx = answer_question(
                        ai_question, candidates, self._api_key, module_title, self._ai_model)

                    if llm_idx is not None:
                        pick = candidates[llm_idx]
                        self._log(f"    Q{qi+1}: AI     [{opts.index(pick)}] {pick[:45]!r}", ep_idx)
                    else:
                        # 4. Fallback: first untried option
                        pick = candidates[0]
                        self._log(f"    Q{qi+1}: rand   [{opts.index(pick)}] {pick[:45]!r}", ep_idx)

                await page.evaluate(_JS_CLICK_RADIO, [qi, opts.index(pick)])
                selected_this_attempt[q_text] = pick

            await self._s.delay(0.5)

            # Submit
            if not await page.evaluate(_JS_SUBMIT):
                self._log(f"  [quiz] Submit button ไม่พบ", ep_idx)
                return 0, False, False

            # ── Poll for results (absolute time, NOT scaled by speed_factor) ──
            # Fast mode would give only 0.5s if we used self._s.delay(2.0) — not enough.
            score = None
            for _poll in range(15):
                await asyncio.sleep(1)
                score = await page.evaluate(_JS_GET_SCORE)
                if score is not None:
                    break
            score = score or 0

            # Check explicitly for "Module assessment passed" banner
            ms_confirmed = await page.evaluate(_JS_MS_CONFIRMED)
            self._log(f"  [quiz] score: {score}%  ms_confirmed={ms_confirmed}", ep_idx)

            # ── Parse results and update cache ─────────────────────────────
            results     = await page.evaluate(_JS_GET_RESULTS)
            dom_learned = 0   # learned from per-question DOM feedback
            wrong_q     = set()

            for r in results:
                q_data = next((q for q in questions if q['qi'] == r['qi']), None)
                if not q_data:
                    continue
                q_text = _clean(q_data['text'])
                opts   = [_clean(o['text']) for o in q_data['options']]
                sel    = _clean(r['selectedText'])
                correct_from_dom = _clean(r.get('correctText', ''))

                # Best case: DOM tells us exactly which option is correct
                if correct_from_dom and correct_from_dom in opts:
                    if mod_cache.get(q_text) != correct_from_dom:
                        mod_cache[q_text] = correct_from_dom
                        dom_learned += 1
                    # If selected ≠ correct → it was wrong → add to tried
                    if sel and sel != correct_from_dom:
                        tried.setdefault(q_text, set()).add(sel)
                    continue

                # No per-question DOM feedback → use isCorrect flag as secondary signal
                if r['isCorrect'] and sel and sel in opts:
                    if mod_cache.get(q_text) != sel:
                        mod_cache[q_text] = sel
                        dom_learned += 1
                elif sel:
                    wrong_q.add(q_text)
                    tried.setdefault(q_text, set()).add(sel)
                    # Elimination: last remaining option must be correct
                    remaining = [t for t in opts if t not in tried.get(q_text, set())]
                    if len(remaining) == 1:
                        if mod_cache.get(q_text) != remaining[0]:
                            mod_cache[q_text] = remaining[0]
                            dom_learned += 1

            if dom_learned:
                self._log(f"  [quiz] DOM feedback: +{dom_learned} คำตอบถูก", ep_idx)

            # ── ms_confirmed OR score == 100%: pass ────────────────────────
            if ms_confirmed or score == 100:
                # Cache all selected answers — they're all correct on a pass
                bulk_cached = 0
                for q_text, sel in selected_this_attempt.items():
                    if sel and mod_cache.get(q_text) != sel:
                        mod_cache[q_text] = sel
                        bulk_cached += 1
                if bulk_cached:
                    self._log(f"  [quiz] PASS — cached {bulk_cached} answers", ep_idx)
                badge_str = " [MS Learn ✓]" if ms_confirmed else ""
                self._log(f"  [quiz] PASS!{badge_str}", ep_idx)

                # Wait for MS Learn backend to record the completion
                await asyncio.sleep(3)

                next_url = await page.evaluate(_JS_GET_NEXT_URL)
                if next_url:
                    await self._s.navigate(page, next_url)
                    await asyncio.sleep(2)
                return 100, True, ms_confirmed

            # ── Score < 100%: detect cache poisoning ───────────────────────
            if used_cache_questions:
                # We used cached answers and still failed → some cache entries are WRONG
                # Remove specifically the cache entries that produced wrong answers
                bad = used_cache_questions & wrong_q
                if not bad:
                    # Can't tell which cache entry was wrong → clear all for this module
                    bad = used_cache_questions
                for q_text in bad:
                    if q_text in mod_cache:
                        del mod_cache[q_text]
                self._log(f"  [quiz] cache เสีย — ลบ {len(bad)} entries", ep_idx)

            if attempt < self._max_retry:
                self._log(f"  [quiz] {score}% — reload + retry", ep_idx)
                await self._s.navigate(page, unit_url)
                await self._s.delay(1.0)

        return score, score == 100, False


def question_with_hint(q_text: str, hint: str) -> str:
    """Append retry hint to question text for the AI prompt."""
    if not hint:
        return q_text
    return f"{q_text}\n[Hint: {hint}]"
