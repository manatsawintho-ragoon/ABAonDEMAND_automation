import asyncio
import threading
import time
import webbrowser
from dataclasses import replace
from pathlib import Path
from typing import Callable, List, Optional

from core.browser import BrowserSession, SpeedMode
from core.lesson_runner import LessonRunner
from core.progress_store import ProgressStore
from core.quiz_runner import QuizRunner
from core.state import AppState, EpisodeStatus
from courses.base_course import CourseConfig
from utils.notify import windows_toast
from utils.screenshot import save_error_screenshot


class AutomationEngine:
    def __init__(
        self,
        course: CourseConfig,
        email: str,
        password: str,
        headless: bool,
        speed: SpeedMode,
        data_dir: Path,
        on_state_change: Callable[[AppState], None],
        ep_filter: Optional[List[int]] = None,  # None = all; [0,3] = only ep 0,3
    ):
        self._course = course
        self._email = email
        self._password = password
        self._headless = headless
        self._speed = speed
        self._data_dir = data_dir
        self._on_state = on_state_change
        self._ep_filter = ep_filter
        self._store = ProgressStore(data_dir / "progress.json")
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._state = AppState(
            episodes=[EpisodeStatus(name=ep.name) for ep in course.episodes],
            total=len(course.episodes),
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
        self._emit(running=True, status_text="กำลังเริ่มต้น…", status_color="#1565C0")
        start_time = time.monotonic()

        # Live elapsed ticker (1 s)
        async def _tick():
            while self._running():
                await asyncio.sleep(1)
                self._emit(elapsed_seconds=time.monotonic() - start_time)

        tick_task = asyncio.create_task(_tick())

        try:
            async with BrowserSession(self._headless, self._speed) as session:
                page = await session.new_page()

                # ── Login ──────────────────────────────────────────────────
                self._emit(status_text="กำลัง Login…")
                if not await self._login(session, page):
                    self._emit(status_text="Login ล้มเหลว", status_color="#c62828", running=False)
                    tick_task.cancel()
                    return
                self._log("✓ Login สำเร็จ")

                # ── Enrollment check ──────────────────────────────────────
                if not await self._check_enrolled(session, page):
                    self._emit(status_text="ยังไม่ได้ enroll course นี้",
                               status_color="#c62828", running=False)
                    tick_task.cancel()
                    return

                # ── Load stored progress ───────────────────────────────────
                done_eps = self._store.get_done_episodes(
                    self._email, self._course.course_id, self._course.min_score)
                ep_details = self._store.get_all_episode_details(
                    self._email, self._course.course_id)

                ep_list = self._course.episodes
                total   = len(ep_list)
                completed = len(done_eps)

                # Restore episode statuses from file
                ep_statuses = list(self._state.episodes)
                for idx, detail in ep_details.items():
                    if idx < len(ep_statuses):
                        ep_statuses[idx] = replace(
                            ep_statuses[idx],
                            status="done" if detail.get("complete") else "failed",
                            score=detail.get("score"),
                            lesson_ok=detail.get("lesson_ok", False),
                            attempts=detail.get("attempts", 0),
                            last_ts=detail.get("ts", ""),
                        )
                self._emit(episodes=ep_statuses, completed=completed, total=total)

                lesson_runner = LessonRunner(
                    session, self._course, self._log,
                    email=self._email, password=self._password)
                quiz_runner = QuizRunner(
                    session, self._course, self._store,
                    self._email, self._log, self._running)

                ep_times: list[float] = []
                session_attempts: dict[int, int] = {}

                for idx, ep in enumerate(ep_list):
                    if not self._running():
                        break

                    # Skip if not in filter
                    if self._ep_filter is not None and idx not in self._ep_filter:
                        continue

                    if idx in done_eps:
                        self._log(f"[{ep.name}] ✓ ข้าม (ผ่านแล้ว {ep_details.get(idx,{}).get('score','?')}%)")
                        continue

                    ep_start = time.monotonic()
                    session_attempts[idx] = 0

                    ep_statuses = list(self._state.episodes)
                    ep_statuses[idx] = replace(ep_statuses[idx], status="running")
                    self._emit(
                        episodes=ep_statuses,
                        current_ep_idx=idx,
                        status_text=f"กำลังทำ: {ep.name}",
                        status_color="#1565C0",
                    )

                    quiz_passed = False
                    final_score = 0
                    lesson_ok   = False

                    try:
                        self._log(f"\n{'─'*48}", idx)
                        self._log(f"  Episode {idx+1}: {ep.name}", idx)

                        # ── Lesson ────────────────────────────────────────
                        self._log("  [lesson] กำลังทำ…", idx)
                        lesson_ok = await lesson_runner.complete(page, ep)
                        self._log(f"  [lesson] {'✓ OK' if lesson_ok else '✗ ยังไม่สำเร็จ'}", idx)

                        if not self._running():
                            break

                        # ── Quiz ──────────────────────────────────────────
                        def _on_attempt(n: int):
                            session_attempts[idx] = n

                        quiz_passed, final_score = await quiz_runner.complete(
                            page, ep, on_attempt=_on_attempt)

                        # ── Retry lesson after quiz passes ────────────────
                        if quiz_passed and not lesson_ok:
                            self._log("  [lesson] quiz ผ่าน → ลอง lesson อีกครั้ง…", idx)
                            lesson_ok = await lesson_runner.complete(page, ep)
                            self._log(f"  [lesson] retry: {'✓' if lesson_ok else '✗'}", idx)

                    except Exception as exc:
                        self._log(f"  [error] {exc}", idx)
                        try:
                            path = await save_error_screenshot(
                                page, f"ep{idx+1}", self._data_dir)
                            self._log(f"  [screenshot] {path}", idx)
                        except Exception:
                            pass
                        quiz_passed, final_score = False, 0

                    # ── Update status ─────────────────────────────────────
                    ep_statuses = list(self._state.episodes)
                    attempts_done = session_attempts.get(idx, 0)

                    if quiz_passed:
                        ep_statuses[idx] = replace(
                            ep_statuses[idx],
                            status="done", score=final_score,
                            lesson_ok=lesson_ok, attempts=attempts_done)
                        self._store.mark_episode(
                            self._email, self._course.course_id,
                            idx, ep.name, final_score,
                            lesson_ok=lesson_ok,
                            attempts=attempts_done,
                            min_score=self._course.min_score)
                        completed += 1
                        self._log(f"  ✓ Episode {idx+1} เสร็จ ({final_score}%)", idx)
                    else:
                        ep_statuses[idx] = replace(
                            ep_statuses[idx],
                            status="failed", score=final_score,
                            lesson_ok=lesson_ok, attempts=attempts_done)
                        self._log(
                            f"  ✗ Episode {idx+1} ยังไม่ผ่าน "
                            f"({final_score}% < {self._course.min_score}%) "
                            f"— cache ยังอยู่ จะลองใหม่รอบหน้า", idx)

                    # ETA
                    ep_elapsed = time.monotonic() - ep_start
                    ep_times.append(ep_elapsed)
                    remaining = total - completed
                    avg = sum(ep_times) / len(ep_times)
                    self._emit(
                        episodes=ep_statuses,
                        completed=completed,
                        elapsed_seconds=time.monotonic() - start_time,
                        eta_seconds=avg * remaining if remaining > 0 else 0.0,
                    )

                # ── Course completion verification ─────────────────────────
                if completed == total and not self._ep_filter:
                    await self._verify_course_complete(session, page)

                # ── Final ─────────────────────────────────────────────────
                elapsed = time.monotonic() - start_time
                if not self._running():
                    self._emit(status_text="หยุดโดยผู้ใช้",
                               status_color="#E65100", running=False,
                               elapsed_seconds=elapsed)
                elif completed == total:
                    self._emit(
                        status_text=f"🎉 เสร็จสิ้นทั้งหมด {total} บท!",
                        status_color="#2E7D32", running=False,
                        elapsed_seconds=elapsed, eta_seconds=0.0)
                    windows_toast("ABA Automator",
                                  f"เสร็จสิ้นทุก episode! ({total}/{total})")
                else:
                    failed = total - completed
                    self._emit(
                        status_text=f"เสร็จ {completed}/{total}  ค้าง {failed} บท",
                        status_color="#F57F17", running=False,
                        elapsed_seconds=elapsed)
                    windows_toast("ABA Automator",
                                  f"เสร็จ {completed}/{total}  ({failed} บทยังไม่ผ่าน)")

        except Exception as exc:
            self._log(f"[fatal] {exc}")
            self._emit(status_text=f"ข้อผิดพลาดร้ายแรง: {exc}",
                       status_color="#c62828", running=False)
        finally:
            tick_task.cancel()

    # ─────────────────────────────────────────────────────────────────────────

    async def _login(self, session: BrowserSession, page) -> bool:
        try:
            await session.navigate(page, self._course.login_url)
            await page.fill("#user_login", self._email)
            await page.fill("#user_pass", self._password)
            await page.click("#wp-submit")
            await page.wait_for_load_state("networkidle", timeout=20000)
            return "wp-login.php" not in page.url
        except Exception as e:
            self._log(f"  [login] {e}")
            return False

    async def _check_enrolled(self, session: BrowserSession, page) -> bool:
        """Returns False only if enrollment is explicitly denied (not just slow load)."""
        try:
            await session.navigate(page, self._course.course_url)
            await self._s_delay(session, 1.0)
            text = await page.evaluate("() => document.body?.innerText || ''")
            if any(w in text.lower() for w in
                   ["not enrolled", "purchase", "buy this", "ยังไม่ได้สมัคร"]):
                self._log(f"  [enroll] ยังไม่ได้ enroll: {self._course.display_name}")
                return False
            return True
        except Exception:
            return True   # Don't block on network error

    @staticmethod
    async def _s_delay(session: BrowserSession, s: float) -> None:
        import asyncio
        await asyncio.sleep(s * session.speed_factor)

    async def _verify_course_complete(self, session: BrowserSession, page) -> None:
        """Navigate to course page and log the completion percentage shown."""
        try:
            await session.navigate(page, self._course.course_url)
            await self._s_delay(session, 1.0)
            text = await page.evaluate("""
                () => {
                    const p = document.querySelector(
                        '.learndash-course-progress,.course-progress,.ld-progress');
                    return p ? p.innerText.trim() : '';
                }
            """)
            if text:
                self._log(f"  [course] สถานะบนเว็บ: {text}")
            else:
                self._log("  [course] ตรวจสอบ course page แล้ว (ไม่พบ progress element)")
        except Exception as e:
            self._log(f"  [course verify] {e}")

    @classmethod
    async def test_login(cls, course: CourseConfig, email: str,
                         password: str) -> bool:
        """Quick login test without running automation. Used by UI Test-Login button."""
        from core.browser import BrowserSession
        try:
            async with BrowserSession(headless=True, speed="fast") as s:
                p = await s.new_page()
                await s.navigate(p, course.login_url)
                await p.fill("#user_login", email)
                await p.fill("#user_pass", password)
                await p.click("#wp-submit")
                await p.wait_for_load_state("networkidle", timeout=15000)
                return "wp-login.php" not in p.url
        except Exception:
            return False
