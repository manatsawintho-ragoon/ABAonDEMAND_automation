"""
MSLearnEngine — Microsoft Learn automation engine.

Same threading interface as AutomationEngine:
  engine.start()  → launches background thread → asyncio.run(_run())
  engine.stop()   → sets stop event
  engine.is_running → bool

Login strategy:
  1. Load saved session from data/mslearn_session.json (Playwright storage_state)
  2. Navigate to learn.microsoft.com — check if already signed in
  3. If not: fill email + password → handle "Stay signed in?" → save session
  4. If MFA appears: switches to visible browser so user can complete it manually,
     then saves the session for future headless runs.

Module completion flow (each module = one "episode"):
  1. Navigate to module page → scrape unit URLs from sidebar TOC
  2. For each unit:
     a. Regular unit  → scroll to bottom → click "Next unit"
     b. Knowledge check → answer with cache → learn correct answers → 100%
  3. Verify module badge earned
"""

import asyncio
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Callable, Dict, List, Optional

from playwright.async_api import async_playwright, BrowserContext, Page
from playwright.async_api import TimeoutError as PwTimeout

from core.browser import BrowserSession, SpeedMode
from core.progress_store import ProgressStore
from core.state import AppState, EpisodeStatus
from courses.mslearn.base_config import MSLearnCourseConfig
from courses.mslearn.unit_runner import MSLearnUnitRunner
from utils.notify import windows_toast
from utils.screenshot import save_error_screenshot
from utils.telemetry import log_event

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_JS_MODULE_BADGE = """
() => {
    // Badge / trophy appears when module is 100% complete
    return !!(
        document.querySelector('.achievement-badge, .badge-earned, .trophy') ||
        document.querySelector('[data-achievement]') ||
        (document.body.innerText || '').toLowerCase().includes('earned')
    );
}
"""

_JS_MODULE_PROGRESS = """
() => {
    const el = document.querySelector(
        '.progress-bar, [role="progressbar"], .module-progress, .unit-progress-container');
    if (!el) return null;
    const aria = el.getAttribute('aria-valuenow') || el.getAttribute('value');
    if (aria !== null) return parseFloat(aria);
    const text = el.innerText || '';
    const m = text.match(/(\\d+)\\s*%/);
    return m ? parseFloat(m[1]) : null;
}
"""

_JS_SIGN_IN_CLICK = """
() => {
    const sels = [
        'a[data-bi-name="login"]',
        'a[href*="login"]',
        'button[data-bi-name="login"]',
    ];
    for (const sel of sels) {
        const el = document.querySelector(sel);
        if (el && el.offsetParent) { el.click(); return true; }
    }
    // Text-based fallback
    for (const el of document.querySelectorAll('a, button')) {
        if (/sign.?in|log.?in/i.test(el.innerText) && el.offsetParent) {
            el.click(); return true;
        }
    }
    return false;
}
"""

_JS_IS_SIGNED_IN = '''
() => {
    if (!location.hostname.includes('learn.microsoft.com')) return false;
    // Positive signals — any one is sufficient
    if (document.querySelector(
        '#mectrl_headerPicture, #mectrl_currentAccount_primary, [data-bi-name="profile-button"], .mectrl_profile_image'
    )) return true;
    if (/welcome back|sign.?out|log.?out/i.test(document.body.innerText || '')) return true;

    // If we definitely see a Sign In button, we are NOT signed in
    const hasSignIn = Array.from(document.querySelectorAll('a, button')).some(el =>
        /^(sign[\\s-]?in|log[\\s-]?in)$/i.test((el.innerText || '').trim()) && el.offsetParent !== null
    );
    if (hasSignIn) return false;

    // If no positive signals found, assume not signed in (conservative)
    return false;
}
'''


class MSLearnEngine:
    """Microsoft Learn automation engine — mirrors AutomationEngine's interface."""

    SESSION_FILE_NAME = "mslearn_session.json"

    def __init__(
        self,
        course: MSLearnCourseConfig,
        email: str,
        password: str,
        headless: bool,
        speed: SpeedMode,
        data_dir: Path,
        on_state_change: Callable[[AppState], None],
        ep_filter: Optional[List[int]] = None,
        api_key: str = "",
        ai_model: str = "",
    ):
        self._course = course
        self._email = email
        self._password = password
        self._headless = headless
        self._speed = speed
        self._data_dir = data_dir
        self._on_state = on_state_change
        self._ep_filter = ep_filter
        self._api_key = api_key
        self._ai_model = ai_model
        self._store = ProgressStore(data_dir / "progress.json")
        self._session_file = data_dir / self.SESSION_FILE_NAME
        self._telemetry = data_dir / "automation.jsonl"
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._start_time: float = 0.0
        self._state = AppState(
            episodes=[EpisodeStatus(name=m.title) for m in course.modules],
            total=len(course.modules),
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._thread_entry, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @classmethod
    async def test_login(cls, course: MSLearnCourseConfig,
                         email: str, password: str) -> bool:
        """Quick login test — used by UI "Test Login" button."""
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                ctx = await browser.new_context(user_agent=_UA, ignore_https_errors=True)
                page = await ctx.new_page()
                await page.goto(course.training_url, wait_until="domcontentloaded",
                                timeout=20000)
                if await page.evaluate(_JS_IS_SIGNED_IN):
                    await browser.close()
                    return True
                ok = await cls._do_login_static(page, email, password)
                await browser.close()
                return ok
        except Exception:
            return False

    # ── Internal ──────────────────────────────────────────────────────────────

    def _running(self) -> bool:
        return not self._stop_event.is_set()

    def _emit(self, **kwargs) -> None:
        self._state = replace(self._state, **kwargs)
        self._on_state(self._state)

    def _log(self, msg: str, ep_idx: int = -1) -> None:
        logs = list(self._state.logs) + [msg]
        ep_logs = dict(self._state.ep_logs)
        if ep_idx >= 0:
            ep_logs[ep_idx] = ep_logs.get(ep_idx, []) + [msg]
        self._state = replace(self._state, logs=logs, ep_logs=ep_logs)
        self._on_state(self._state)

    def _thread_entry(self) -> None:
        asyncio.run(self._run())

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def _run(self) -> None:
        self._emit(running=True, status_text="กำลังเริ่มต้น MS Learn…",
                   status_color="#1565C0")
        self._start_time = time.monotonic()
        log_event(self._telemetry, "session_start",
                  email=self._email, course=self._course.course_id)

        try:
            # Determine headless mode — if no saved session, force visible so user can log in
            has_session = self._session_file.exists()
            run_headless = self._headless and has_session

            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=run_headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )

                # Load saved session or create fresh context
                ctx_kwargs = dict(user_agent=_UA, ignore_https_errors=True)
                if has_session:
                    try:
                        ctx_kwargs["storage_state"] = str(self._session_file)
                    except Exception:
                        pass

                ctx = await browser.new_context(**ctx_kwargs)
                session = BrowserSession(self._headless, self._speed)
                session._ctx = ctx   # inject context so navigate/delay work
                page = await ctx.new_page()

                # ── Login ──────────────────────────────────────────────────
                self._emit(status_text="กำลัง Login MS Learn…")
                ok = await self._login(session, page, ctx, browser)
                if not ok:
                    self._emit(status_text="Login ล้มเหลว",
                               status_color="#c62828", running=False)
                    await browser.close()
                    return
                self._log("✓ Login MS Learn สำเร็จ")
                if self._api_key:
                    from utils.llm_answerer import DEFAULT_MODEL
                    model_name = self._ai_model or DEFAULT_MODEL
                    self._log(f"  [AI] OpenRouter พร้อม — {model_name}")
                else:
                    self._log("  [AI] ไม่มี OpenRouter Key — ใช้การสุ่ม+elimination แทน")

                # Save updated session
                try:
                    await ctx.storage_state(path=str(self._session_file))
                except Exception:
                    pass

                # ── Load stored progress ───────────────────────────────────
                done_eps = self._store.get_done_episodes(
                    self._email, self._course.course_id, self._course.min_score,
                    require_ms_confirmed=True)
                ep_details = self._store.get_all_episode_details(
                    self._email, self._course.course_id)

                modules = self._course.modules
                total = len(modules)
                completed = len(done_eps)

                ep_statuses = list(self._state.episodes)
                for idx, detail in ep_details.items():
                    if idx < len(ep_statuses):
                        ep_statuses[idx] = replace(
                            ep_statuses[idx],
                            status="done" if detail.get("complete") else "failed",
                            score=detail.get("score"),
                            attempts=detail.get("attempts", 0),
                            last_ts=detail.get("ts", ""),
                        )
                self._emit(episodes=ep_statuses, completed=completed, total=total)

                # Build shared answer cache (persisted per module_id in progress.json)
                answer_cache: Dict[str, Dict] = {}
                for mod in modules:
                    cached = self._store.get_answer_cache(
                        self._email, self._course.course_id, mod.quiz_post_id)
                    # We use module_id as sub-key within the cache dict
                    cached2 = self._store.get_answer_cache(
                        self._email, self._course.course_id, hash(mod.module_id) & 0xFFFF)
                    answer_cache[mod.module_id] = {**cached, **cached2}

                unit_runner = MSLearnUnitRunner(
                    session=session,
                    on_log=self._log,
                    stop_flag=self._running,
                    answer_cache=answer_cache,
                    max_retry=self._course.max_retry,
                    api_key=self._api_key,
                    ai_model=self._ai_model,
                )

                ep_times: list[float] = []

                for idx, mod in enumerate(modules):
                    if not self._running():
                        break
                    if self._ep_filter is not None and idx not in self._ep_filter:
                        continue
                    if idx in done_eps:
                        self._log(f"[{mod.title}] ✓ ข้าม (ผ่านแล้ว)")
                        continue

                    ep_start = time.monotonic()
                    ep_statuses = list(self._state.episodes)
                    ep_statuses[idx] = replace(ep_statuses[idx], status="running")
                    self._emit(
                        episodes=ep_statuses,
                        current_ep_idx=idx,
                        status_text=f"กำลังทำ: {mod.title}",
                        status_color="#1565C0",
                    )

                    module_passed = False
                    final_score = 0
                    ms_confirmed = False

                    try:
                        self._log(f"\n{'─'*48}", idx)
                        self._log(f"  Module {idx+1}: {mod.title}", idx)

                        module_passed, final_score, ms_confirmed = await unit_runner.complete_module(
                            page, mod.url, mod.module_id, idx, mod.title)

                        # Persist answer cache after module completes
                        mod_cache = answer_cache.get(mod.module_id, {})
                        if mod_cache:
                            self._store.save_answer_cache(
                                self._email, self._course.course_id,
                                hash(mod.module_id) & 0xFFFF, mod_cache)

                        self._log(f"  [module] → {final_score}% {'✓' if module_passed else '✗'}", idx)

                    except Exception as exc:
                        self._log(f"  [error] {exc}", idx)
                        try:
                            path = await save_error_screenshot(
                                page, f"mslearn_mod{idx+1}", self._data_dir)
                            self._log(f"  [screenshot] {path}", idx)
                        except Exception:
                            pass

                    # ── Update status ──────────────────────────────────────
                    ep_statuses = list(self._state.episodes)
                    ep_elapsed = time.monotonic() - ep_start
                    if module_passed:
                        ep_statuses[idx] = replace(ep_statuses[idx],
                            status="done", score=final_score)
                        self._store.mark_episode(
                            self._email, self._course.course_id,
                            idx, mod.title, final_score,
                            lesson_ok=True, attempts=1,
                            min_score=self._course.min_score,
                            ms_confirmed=ms_confirmed)
                        completed += 1
                        badge_str = " [MS Learn ✓]" if ms_confirmed else " [ยังไม่ confirmed]"
                        self._log(f"  ✓ Module {idx+1} เสร็จ ({final_score}%){badge_str}", idx)
                        log_event(self._telemetry, "module_complete",
                                  email=self._email, course=self._course.course_id,
                                  module_id=mod.module_id, score=final_score,
                                  elapsed_s=round(ep_elapsed, 1))
                    else:
                        ep_statuses[idx] = replace(ep_statuses[idx],
                            status="failed", score=final_score)
                        self._log(f"  ✗ Module {idx+1} ไม่สำเร็จ ({final_score}%)", idx)
                        log_event(self._telemetry, "module_failed",
                                  email=self._email, course=self._course.course_id,
                                  module_id=mod.module_id, score=final_score,
                                  elapsed_s=round(ep_elapsed, 1))

                    ep_times.append(ep_elapsed)
                    remaining = total - completed
                    avg = sum(ep_times) / len(ep_times)
                    self._emit(
                        episodes=ep_statuses,
                        completed=completed,
                        elapsed_seconds=time.monotonic() - self._start_time,
                        eta_seconds=avg * remaining if remaining > 0 else 0.0,
                    )

                elapsed = time.monotonic() - self._start_time
                if not self._running():
                    self._emit(status_text="หยุดโดยผู้ใช้",
                               status_color="#E65100", running=False,
                               elapsed_seconds=elapsed)
                elif completed == total:
                    self._emit(
                        status_text=f"🎉 เสร็จสิ้นทุก module! ({total}/{total})",
                        status_color="#2E7D32", running=False,
                        elapsed_seconds=elapsed, eta_seconds=0.0)
                    windows_toast("MS Learn Automator",
                                  f"เสร็จสิ้นทุก module! ({total}/{total})")
                else:
                    failed = total - completed
                    self._emit(
                        status_text=f"เสร็จ {completed}/{total}  ค้าง {failed} module",
                        status_color="#F57F17", running=False,
                        elapsed_seconds=elapsed)

                await browser.close()

        except Exception as exc:
            self._log(f"[fatal] {exc}")
            self._emit(status_text=f"ข้อผิดพลาด: {exc}",
                       status_color="#c62828", running=False)

    # ── Login ─────────────────────────────────────────────────────────────────

    async def _login(self, session: BrowserSession, page: Page,
                     ctx: BrowserContext, browser) -> bool:
        async def is_signed_in():
            try:
                # Need to be on the right domain for the check to make sense
                if 'learn.microsoft.com' not in page.url:
                    return False
                return await page.evaluate(_JS_IS_SIGNED_IN)
            except Exception:
                return False

        try:
            await page.goto(self._course.training_url,
                            wait_until="load", timeout=30000)
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except PwTimeout:
                pass
            await session.delay(2.0)  # extra wait for Microsoft header JS to render

            if await is_signed_in():
                self._log("  [login] session ยังใช้งานได้")
                return True

            # Click sign-in
            self._log("  [login] กำลัง sign in…")
            try:
                clicked = await page.evaluate(_JS_SIGN_IN_CLICK)
            except Exception as e:
                # If context is destroyed immediately, it usually means navigation started
                if "destroyed" in str(e).lower() or "navigation" in str(e).lower():
                    clicked = True
                else:
                    clicked = False

            if not clicked:
                await page.goto(
                    "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
                    "?client_id=18fbca16-2224-45f6-85b0-f7bf2b39b3f3"
                    "&response_type=code&scope=openid%20profile%20email"
                    f"&login_hint={self._email}",
                    wait_until="load", timeout=25000)

            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except PwTimeout:
                pass
            await session.delay(1.5)

            # Re-check: clicking sign-in might redirect back if already authenticated
            if await is_signed_in():
                self._log("  [login] ✓ พบว่า login อยู่แล้ว")
                return True

            ok = await self._do_login_static(page, self._email, self._password)

            # _do_login_static may return False if no login form found (already signed in)
            if not ok:
                await asyncio.sleep(2.0)
                if await is_signed_in():
                    self._log("  [login] ✓ session ใช้งานได้ (detected หลัง login attempt)")
                    return True

            if not ok:
                if not self._headless:
                    self._log("  [login] รอผู้ใช้ complete MFA / ยืนยันตัวตน (สูงสุด 3 นาที)…")
                    for _ in range(180):
                        if not self._running():  # Stop button check
                            return False
                        await asyncio.sleep(1)
                        if await is_signed_in():
                            ok = True
                            break
                    if not ok:
                        self._log("  [login] timeout รอ MFA")
                        ok = await is_signed_in()
                else:
                    self._session_file.unlink(missing_ok=True)
                    self._log("  [login] ต้องการ MFA — ปิด Headless option แล้วรันใหม่ครั้งเดียว")

            return ok

        except Exception as e:
            self._log(f"  [login] {e}")
            return False

    @staticmethod
    async def _do_login_static(page: Page, email: str, password: str) -> bool:
        """Fill email + password on Microsoft login page."""
        try:
            # Email step
            email_sel = "input[type='email'], #i0116, input[name='loginfmt']"
            try:
                await page.wait_for_selector(email_sel, timeout=8000)
                await page.fill(email_sel, email)
                # Click Next
                next_sel = "input[value='Next'], #idSIButton9, input[type='submit']"
                await page.click(next_sel)
                await page.wait_for_load_state("domcontentloaded", timeout=12000)
                try:
                    await page.wait_for_load_state("networkidle", timeout=6000)
                except PwTimeout:
                    pass
                await asyncio.sleep(1.0)
            except PwTimeout:
                pass  # might already be on password page

            # Password step
            pw_sel = "input[type='password'], #i0118, input[name='passwd']"
            try:
                await page.wait_for_selector(pw_sel, timeout=8000)
                await page.fill(pw_sel, password)
                sign_in_sel = "input[value='Sign in'], #idSIButton9, input[type='submit']"
                await page.click(sign_in_sel)
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except PwTimeout:
                    pass
                await asyncio.sleep(1.5)
            except PwTimeout:
                pass

            # "Stay signed in?" prompt
            try:
                yes_btn = page.locator("#idSIButton9:visible")
                if await yes_btn.count() > 0:
                    await yes_btn.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                    await asyncio.sleep(1.0)
            except Exception:
                pass

            return await page.evaluate(_JS_IS_SIGNED_IN)

        except Exception:
            return False
