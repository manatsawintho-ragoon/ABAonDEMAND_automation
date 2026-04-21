import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from playwright.async_api import Page, TimeoutError as PwTimeout

from core.browser import BrowserSession
from core.progress_store import ProgressStore
from courses.base_course import CourseConfig, EpisodeConfig

# ── JavaScript helpers ────────────────────────────────────────────────────────

_JS_CURRENT_Q = """
() => {
    const items = document.querySelectorAll('li.wpProQuiz_listItem');
    for (const item of items) {
        const s = window.getComputedStyle(item);
        if (s.display === 'none' || s.visibility === 'hidden') continue;

        const qEl = item.querySelector('.wpProQuiz_question_text');
        if (!qEl) continue;
        const qText = qEl.innerText.trim();
        if (!qText) continue;

        const optEls = item.querySelectorAll(
            'ul.wpProQuiz_questionList > li.wpProQuiz_questionListItem');
        if (!optEls.length) continue;

        const inp0 = optEls[0].querySelector('input');
        const qType = inp0 ? inp0.type : 'radio';

        const optTexts = Array.from(optEls).map(o => {
            const tmp = document.createElement('div');
            tmp.innerHTML = o.innerHTML;
            tmp.querySelectorAll('input').forEach(e => e.remove());
            return tmp.innerText.trim();
        });

        return { qText, n: optEls.length, optTexts, qType };
    }
    return null;
}
"""

_JS_CLICK_OPTS = """
(indices) => {
    const items = document.querySelectorAll('li.wpProQuiz_listItem');
    for (const item of items) {
        const s = window.getComputedStyle(item);
        if (s.display === 'none' || s.visibility === 'hidden') continue;

        const opts = item.querySelectorAll(
            'ul.wpProQuiz_questionList > li.wpProQuiz_questionListItem');
        if (!opts.length) continue;

        opts.forEach(opt => {
            const inp = opt.querySelector('input');
            if (inp && inp.type === 'checkbox' && inp.checked) inp.click();
        });
        let clicked = 0;
        for (const idx of indices) {
            const inp = opts[idx]?.querySelector('input');
            if (inp) { inp.click(); clicked++; }
        }
        return clicked;
    }
    return 0;
}
"""

_JS_VERIFY = """
() => {
    const items = document.querySelectorAll('li.wpProQuiz_listItem');
    for (const item of items) {
        const s = window.getComputedStyle(item);
        if (s.display === 'none' || s.visibility === 'hidden') continue;
        const inputs = item.querySelectorAll('ul.wpProQuiz_questionList input');
        return Array.from(inputs).some(i => i.checked);
    }
    return false;
}
"""

_JS_WAIT_FEEDBACK = """
() => {
    const isVis = el => {
        if (!el) return false;
        const s = window.getComputedStyle(el);
        return s.display !== 'none' && s.visibility !== 'hidden' && parseFloat(s.opacity) > 0;
    };
    const items = document.querySelectorAll('li.wpProQuiz_listItem');
    for (const item of items) {
        const s = window.getComputedStyle(item);
        if (s.display === 'none' || s.visibility === 'hidden') continue;
        const ok  = item.querySelector('.wpProQuiz_correct');
        const bad = item.querySelector('.wpProQuiz_incorrect');
        if (isVis(ok) || isVis(bad)) return true;
    }
    return false;
}
"""

_JS_INLINE = """
() => {
    const isVis = el => {
        if (!el) return false;
        const s = window.getComputedStyle(el);
        return s.display !== 'none' && s.visibility !== 'hidden' && parseFloat(s.opacity) > 0;
    };
    const items = document.querySelectorAll('li.wpProQuiz_listItem');
    for (const item of items) {
        const s = window.getComputedStyle(item);
        if (s.display === 'none' || s.visibility === 'hidden') continue;
        const ok  = item.querySelector('.wpProQuiz_correct');
        const bad = item.querySelector('.wpProQuiz_incorrect');
        if (isVis(ok))  return 'correct';
        if (isVis(bad)) return 'incorrect';
    }
    return null;
}
"""

# POST-QUIZ: return ordered list [{qText, status}] matching DOM order.
# Using a list (not dict) lets Python do positional matching to q_order,
# which correctly handles multiple questions with identical q_text.
_JS_POST_RESULTS = """
() => {
    const isVis = el => {
        if (!el) return false;
        const s = window.getComputedStyle(el);
        return s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0';
    };
    const out = [];
    document.querySelectorAll('li.wpProQuiz_listItem').forEach(item => {
        const qEl = item.querySelector('.wpProQuiz_question_text');
        if (!qEl) return;
        const qText = qEl.innerText.trim();
        if (!qText) return;
        const ok  = item.querySelector('.wpProQuiz_correct');
        const bad = item.querySelector('.wpProQuiz_incorrect');
        let status = null;
        if (isVis(ok)) status = 'correct';
        else if (isVis(bad)) status = 'incorrect';
        out.push({ qText, status });
    });
    return out;
}
"""

_JS_REVIEW = """
() => {
    const sels = [
        '.wpProQuiz_reviewDiv .wpProQuiz_reviewQuestion ol li',
        '.wpProQuiz_reviewQuestion ol li',
        '.wpProQuiz_review ol li',
    ];
    for (const sel of sels) {
        const lis = document.querySelectorAll(sel);
        if (!lis.length) continue;
        const r = {};
        lis.forEach((li, i) => {
            if (li.classList.contains('wpProQuiz_reviewQuestionSolvedCorrect'))
                r[i] = 'correct';
            else if (li.classList.contains('wpProQuiz_reviewQuestionSolvedIncorrect'))
                r[i] = 'incorrect';
        });
        if (Object.keys(r).length) return { type: 'review', data: r };
    }
    return { type: 'none', data: {} };
}
"""

_JS_LOCK_TEXT = """
() => (document.querySelector('.wpProQuiz_lock')?.innerText || '').toLowerCase()
"""

_JS_RETAKE_LIMIT = """
() => /maximum.*attempt|no.*more.*attempt|retake.*limit/i.test(
    document.body?.innerText || '')
"""

# Normalize messy innerText (tabs/newlines) → single clean string
def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


class QuizRunner:
    """
    Smart quiz answering with text-keyed answer cache.

    Cache key   = question TEXT (+ "[N]" suffix for duplicate q_texts)
    Cache value = correct option TEXT (radio) or list of texts (checkbox)

    Learning sources (in priority order):
      1. Inline feedback after each "Check" click
      2. Post-quiz: positional list matched to q_order (handles duplicate q_texts)
      3. Review panel fallback (by position index)
      4. Elimination: N-1 options tried wrong → last must be correct
    """

    def __init__(self, session: BrowserSession, course: CourseConfig,
                 store: ProgressStore, email: str,
                 on_log: Callable[[str], None],
                 stop_flag_fn: Callable[[], bool]):
        self._s       = session
        self._c       = course
        self._store   = store
        self._email   = email
        self._log     = on_log
        self._running = stop_flag_fn

    async def complete(self, page: Page, ep: EpisodeConfig,
                       on_attempt: Optional[Callable[[int], None]] = None
                       ) -> Tuple[bool, int]:
        correct_map: Dict[str, Any]            = self._store.get_answer_cache(
            self._email, self._c.course_id, ep.quiz_post_id)
        tried_map:   Dict[str, Set[str]]       = {}
        tried_combos: Dict[str, List[frozenset]] = {}

        if correct_map:
            self._log(f"  [quiz] cache: รู้คำตอบ {len(correct_map)} ข้อ")

        score = 0
        for attempt in range(1, self._c.max_retry + 1):
            if not self._running():
                return False, score

            if on_attempt:
                on_attempt(attempt)
            self._log(f"  [quiz] ── attempt {attempt}/{self._c.max_retry} ──")

            score, new_correct = await self._take_once(
                page, ep, correct_map, tried_map, tried_combos)

            if new_correct:
                correct_map.update(new_correct)
                self._store.save_answer_cache(
                    self._email, self._c.course_id, ep.quiz_post_id, correct_map)
                self._log(f"  [quiz] เรียนรู้ใหม่ +{len(new_correct)} ข้อ  "
                          f"(cache รวม: {len(correct_map)} ข้อ)")

            self._log(f"  [quiz] คะแนน {score}% / {self._c.min_score}%  "
                      f"{'✓ ผ่าน!' if score >= self._c.min_score else '✗ ยังไม่ผ่าน'}")

            if score >= self._c.min_score:
                return True, score

            if attempt >= self._c.max_retry:
                break

            if await page.evaluate(_JS_RETAKE_LIMIT):
                self._log("  [quiz] ถึงจำนวน retake สูงสุดของเว็บ — หยุด")
                break

            n_unknown = sum(1 for k in tried_map if k not in correct_map)
            self._log(f"  [quiz] cache: {len(correct_map)} ข้อ  "
                      f"| ยังไม่รู้: {n_unknown} ข้อ  → restart")
            await self._s.delay(0.8)

            if not await self._restart(page, ep.quiz_url):
                self._log("  [quiz] restart ไม่สำเร็จ")
                break

        return score >= self._c.min_score, score

    # ─────────────────────────────────────────────────────────────────────────

    async def _take_once(self, page: Page, ep: EpisodeConfig,
                         correct_map: Dict[str, Any],
                         tried_map: Dict[str, Set[str]],
                         tried_combos: Dict[str, List[frozenset]]
                         ) -> Tuple[int, dict]:
        new_correct: dict = {}
        q_order:     List[str]      = []   # q_key per question in answer order
        chosen_texts: Dict[str, Any]       = {}
        opts_texts:   Dict[str, List[str]] = {}
        q_seen_count: Dict[str, int]       = {}  # tracks duplicate q_texts

        try:
            await self._s.navigate(page, ep.quiz_url)
            await self._s.delay(0.5)

            # Lock check
            if await page.locator(self._c.quiz_lock_sel).is_visible():
                lock_txt = await page.evaluate(_JS_LOCK_TEXT)
                if any(w in lock_txt for w in ["already", "complet", "pass"]):
                    self._log("  [quiz] lock → quiz ผ่านแล้ว")
                    return 100, {}
                self._log("  [quiz] lock → prerequisite ไม่ครบ")
                return 0, {}

            start_btn = page.locator(self._c.start_btn_sel)
            if not await start_btn.is_visible(timeout=4000):
                self._log("  [quiz] ไม่พบปุ่ม Start")
                return 0, {}

            await start_btn.click()
            await self._s.delay(0.8)

            # ── Answer loop ───────────────────────────────────────────────
            for _guard in range(40):
                q_data = await page.evaluate(_JS_CURRENT_Q)
                if not q_data:
                    break

                q_text   = q_data["qText"]
                n_opts   = q_data["n"]
                # Normalize whitespace in option texts (innerText can have \n\t artifacts)
                opt_txts = [_clean(t) for t in q_data["optTexts"]]
                q_type   = q_data["qType"]

                if not q_text or not opt_txts or n_opts == 0:
                    self._log(f"  [quiz] Q{len(q_order)+1}: ไม่พบข้อมูล → หยุด")
                    break

                # Build unique key when multiple questions share the same q_text
                q_seen_count[q_text] = q_seen_count.get(q_text, 0) + 1
                cnt = q_seen_count[q_text]
                q_key = q_text if cnt == 1 else f"{q_text}\n[{cnt}]"

                opts_texts[q_key] = opt_txts
                q_num = len(q_order) + 1

                # Choose answer
                if q_type == "checkbox":
                    indices, chosen_t = self._choose_checkbox(
                        q_key, opt_txts, correct_map, tried_combos)
                else:
                    indices, chosen_t = self._choose_radio(
                        q_key, opt_txts, correct_map, tried_map)

                cache_tag = "✓cache" if q_key in correct_map else "?new"
                dup_tag   = f" #{cnt}" if cnt > 1 else ""
                q_short   = _clean(q_text)[:55]
                chosen_short = (str(chosen_t) if not isinstance(chosen_t, list)
                                else str(chosen_t))[:40]
                self._log(
                    f"  [quiz] Q{q_num}{dup_tag}: {q_short}…  "
                    f"({n_opts} opts, {q_type})  [{cache_tag}]")
                self._log(
                    f"  [quiz]   opts={opt_txts}  "
                    f"→ เลือก [{','.join(str(i) for i in indices)}] {chosen_short!r}")

                q_order.append(q_key)
                chosen_texts[q_key] = chosen_t

                # Click + verify
                clicked = await page.evaluate(_JS_CLICK_OPTS, indices)
                if not clicked:
                    self._log("  [quiz]   click ล้มเหลว! ลองใหม่")
                await self._s.delay(0.2)
                if not await page.evaluate(_JS_VERIFY):
                    await page.evaluate(_JS_CLICK_OPTS, indices)
                    await self._s.delay(0.2)

                # Per-question Check button (not all quiz types have this)
                chk = page.locator("input[name=check]:visible")
                if await chk.count() > 0:
                    await chk.first.click()
                    try:
                        await page.wait_for_function(_JS_WAIT_FEEDBACK, timeout=3000)
                    except PwTimeout:
                        await self._s.delay(0.4)
                    inline = await page.evaluate(_JS_INLINE)
                    if inline:
                        self._log(f"  [quiz]   inline: {inline}")
                        self._apply_feedback(
                            inline, q_key, chosen_t, opt_txts, q_type,
                            correct_map, tried_map, tried_combos, new_correct)

                # Next button
                nxt = page.locator("input[name=next]:visible")
                if await nxt.count() > 0:
                    await nxt.first.click()
                    await self._s.delay(0.3)

            self._log(f"  [quiz] ตอบครบ {len(q_order)} ข้อ")

            # ── End quiz ──────────────────────────────────────────────────
            for btn_name in ["endQuizSummary", "endQuiz"]:
                btn = page.locator(f"input[name={btn_name}]:visible")
                if await btn.count() > 0:
                    await btn.first.click()
                    await self._s.delay(1.5)
                    break

            try:
                await page.locator(".wpProQuiz_results").wait_for(
                    state="visible", timeout=8000)
            except PwTimeout:
                pass
            await self._s.delay(0.6)

            score = await self._parse_score(page)

            # ── Post-quiz: positional list → match to q_order by index ────
            # Using a list (not dict) correctly handles duplicate q_texts
            post_list: List[dict] = await page.evaluate(_JS_POST_RESULTS)
            n_ok  = sum(1 for it in post_list if it.get('status') == 'correct')
            n_bad = sum(1 for it in post_list if it.get('status') == 'incorrect')
            n_none = sum(1 for it in post_list if not it.get('status'))
            self._log(f"  [quiz] post-quiz: {len(post_list)} ข้อ  "
                      f"✓{n_ok}  ✗{n_bad}  ?{n_none}")

            # Build q_key → status using positional matching
            post_by_key: Dict[str, str] = {}
            for i, item in enumerate(post_list):
                if i >= len(q_order):
                    break
                q_key_i = q_order[i]
                if item.get('status'):
                    post_by_key[q_key_i] = item['status']

            # Review panel fallback — fills gaps not covered by post_list
            rev = await page.evaluate(_JS_REVIEW)
            if rev.get("type") == "review":
                rev_count = 0
                for ri_s, status in rev["data"].items():
                    ri = int(ri_s)
                    if ri < len(q_order):
                        q_key_r = q_order[ri]
                        if q_key_r not in post_by_key:
                            post_by_key[q_key_r] = status
                            rev_count += 1
                if rev_count:
                    self._log(f"  [quiz] review panel: เพิ่มอีก {rev_count} ข้อ")

            # Learn from combined results
            learned = 0
            result_lines = []
            for q_key_r, status in post_by_key.items():
                ch = chosen_texts.get(q_key_r)
                op = opts_texts.get(q_key_r, [])
                if ch is not None:
                    q_type_guess = "checkbox" if isinstance(ch, list) else "radio"
                    before = len(new_correct)
                    self._apply_feedback(
                        status, q_key_r, ch, op, q_type_guess,
                        correct_map, tried_map, tried_combos, new_correct)
                    if len(new_correct) > before:
                        learned += 1
                mark = "✓" if status == "correct" else "✗"
                ch_short = (str(ch) if not isinstance(ch, list) else str(ch))[:20]
                result_lines.append(f"{mark}{ch_short!r}")
            self._log(f"  [quiz] results: {' | '.join(result_lines)}")
            if learned:
                self._log(f"  [quiz] เรียนจาก post-quiz: +{learned} ข้อ")

            return score, new_correct

        except Exception as e:
            self._log(f"  [quiz error] {e}")
            import traceback
            self._log(f"  [quiz trace] {traceback.format_exc()[-300:]}")
            return 0, {}

    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _choose_radio(q_key: str, opt_txts: List[str],
                      correct_map: dict,
                      tried_map: Dict[str, Set[str]]) -> Tuple[List[int], str]:
        if q_key in correct_map:
            target = correct_map[q_key]
            # Legacy format: old cache stored integer index instead of text
            if isinstance(target, int):
                if 0 <= target < len(opt_txts):
                    text_target = opt_txts[target]
                    correct_map[q_key] = text_target
                    return [target], text_target
                del correct_map[q_key]
            else:
                idx = next((i for i, t in enumerate(opt_txts) if t == target), None)
                if idx is not None:
                    return [idx], target
                del correct_map[q_key]  # Text not in options — purge stale

        tried = {t for t in tried_map.get(q_key, set()) if t in opt_txts}
        tried_map[q_key] = tried

        untried = [t for t in opt_txts if t not in tried]
        chosen = untried[0] if untried else opt_txts[0]
        return [opt_txts.index(chosen)], chosen

    @staticmethod
    def _choose_checkbox(q_key: str, opt_txts: List[str],
                         correct_map: dict,
                         tried_combos: Dict[str, List[frozenset]]
                         ) -> Tuple[List[int], List[str]]:
        if q_key in correct_map:
            correct_list = correct_map[q_key]
            if isinstance(correct_list, list):
                if correct_list and isinstance(correct_list[0], int):
                    converted = [opt_txts[i] for i in correct_list
                                 if 0 <= i < len(opt_txts)]
                    if converted:
                        correct_map[q_key] = converted
                        correct_list = converted
                indices = [i for i, t in enumerate(opt_txts) if t in correct_list]
                if indices:
                    return indices, correct_list
            del correct_map[q_key]

        tried = tried_combos.get(q_key, [])
        for combo in [frozenset({t}) for t in opt_txts] + [frozenset(opt_txts)]:
            if combo not in tried:
                texts = list(combo)
                return [i for i, t in enumerate(opt_txts) if t in combo], texts
        return list(range(len(opt_txts))), opt_txts

    @staticmethod
    def _apply_feedback(status: Optional[str],
                        q_key: str, chosen: Any,
                        opt_txts: List[str], q_type: str,
                        correct_map: dict,
                        tried_map: Dict[str, Set[str]],
                        tried_combos: Dict[str, List[frozenset]],
                        new_correct: dict) -> None:
        if not status or chosen is None:
            return
        if q_type == "checkbox" or isinstance(chosen, list):
            combo = frozenset(chosen) if isinstance(chosen, list) else frozenset()
            if status == "correct":
                if correct_map.get(q_key) != list(chosen):
                    correct_map[q_key] = list(chosen)
                    new_correct[q_key] = list(chosen)
            elif status == "incorrect":
                tried_combos.setdefault(q_key, [])
                if combo not in tried_combos[q_key]:
                    tried_combos[q_key].append(combo)
        else:
            if status == "correct":
                if correct_map.get(q_key) != chosen:
                    correct_map[q_key] = chosen
                    new_correct[q_key] = chosen
            elif status == "incorrect":
                tried_map.setdefault(q_key, set()).add(chosen)
                remaining = [t for t in opt_txts if t not in tried_map[q_key]]
                if len(remaining) == 1:
                    correct_map[q_key] = remaining[0]
                    new_correct[q_key] = remaining[0]

    async def _parse_score(self, page: Page) -> int:
        text = await page.evaluate(
            "() => document.querySelector('.wpProQuiz_results')?.innerText || ''")
        self._log(f"  [quiz] score text: {repr(text[:80])}")
        m = re.search(r'(\d+)\s*(?:out of|\/)\s*(\d+)', text, re.IGNORECASE)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            return round(a / b * 100) if b else 0
        m = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
        if m:
            return round(float(m.group(1)))
        m = re.search(r'(\d+)\D+(\d+)', text)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            return round(a / b * 100) if b else 0
        return 0

    async def _restart(self, page: Page, quiz_url: str) -> bool:
        for sel in self._c.restart_sels:
            try:
                btn = page.locator(f"{sel}:visible")
                if await btn.count() > 0:
                    await btn.first.click()
                    await page.wait_for_load_state("networkidle", timeout=10000)
                    await self._s.delay(0.5)
                    if await page.locator(self._c.start_btn_sel).is_visible(timeout=3000):
                        return True
            except Exception:
                continue
        await self._s.navigate(page, quiz_url)
        await self._s.delay(0.5)
        if await page.locator(self._c.quiz_lock_sel).is_visible():
            return False
        return await page.locator(self._c.start_btn_sel).is_visible(timeout=3000)

    async def is_locked(self, page: Page, quiz_url: str) -> bool:
        try:
            await self._s.navigate(page, quiz_url)
            await self._s.delay(0.4)
            return await page.locator(self._c.quiz_lock_sel).is_visible()
        except Exception:
            return False
