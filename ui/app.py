import asyncio
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
from typing import Dict, Optional

from core.engine import AutomationEngine
from core.progress_store import ProgressStore
from core.state import AppState, EpisodeStatus
from courses.base_course import CourseConfig
from ui import theme
from ui.control_bar import ControlBar
from ui.credentials_panel import CredentialsPanel
from ui.episode_grid import EpisodeGrid
from ui.header import Header
from ui.log_panel import LogPanel
from ui.options_panel import OptionsPanel
from ui.timing_panel import TimingPanel
from utils.profile_store import ProfileStore
from utils.settings_store import SettingsStore

DATA_DIR = Path(__file__).parent.parent / "data"


class App(tk.Tk):
    def __init__(self, courses: Dict[str, CourseConfig]):
        super().__init__()

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._settings = SettingsStore(DATA_DIR / "settings.json")
        saved = self._settings.load()

        # Apply dark mode before building UI
        if saved.get("dark_mode"):
            theme.apply_mode("dark")

        self.title("ABA on Demand Automator")
        self.configure(bg=theme.BG())
        self.resizable(True, True)
        self.minsize(860, 680)

        geo = saved.get("window_geometry", "")
        if geo:
            try:
                self.geometry(geo)
            except Exception:
                pass

        self._courses = courses
        self._current_course = next(iter(courses.values()))
        self._engine: Optional[AutomationEngine] = None
        self._profile_store = ProfileStore(DATA_DIR / "profiles.json")
        self._store = ProgressStore(DATA_DIR / "progress.json")

        self._build()
        self._load_stored_progress()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Auto-start
        if saved.get("auto_start") and self._creds.email and self._creds.password:
            self.after(1500, self._start)

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # Header
        self._header = Header(self, self._courses,
                              on_course_change=self._on_course_change)
        self._header.pack(fill="x")

        # Body
        body = tk.Frame(self, bg=theme.BG())
        body.pack(fill="both", expand=True, padx=10, pady=8)

        left  = tk.Frame(body, bg=theme.BG())
        left.pack(side="left", fill="y")
        right = tk.Frame(body, bg=theme.BG())
        right.pack(side="right", fill="both", expand=True, padx=(10, 0))

        # ── Left column ───────────────────────────────────────────────────
        self._creds = CredentialsPanel(
            left, self._profile_store,
            on_profile_select=self._on_profile_select)
        self._creds.pack(fill="x", pady=(0, 8))

        self._opts = OptionsPanel(
            left, self._settings,
            on_dark_mode=self._on_dark_mode)
        self._opts.pack(fill="x", pady=(0, 8))

        self._ctrl = ControlBar(
            left,
            on_start=self._start,
            on_stop=self._stop,
            on_test_login=self._test_login)
        self._ctrl.pack(fill="x", pady=(0, 8))

        self._timing = TimingPanel(left)
        self._timing.pack(fill="x", pady=(0, 8))

        # Reset buttons
        reset_frame = tk.Frame(left, bg=theme.BG())
        reset_frame.pack(fill="x")
        tk.Button(reset_frame, text="🗑 Reset ทั้งหมด", font=theme.FONT_SMALL,
                  bg=theme.ERROR(), fg="white", relief="flat", padx=8, pady=4,
                  command=self._reset_all).pack(side="left", padx=(0, 6))
        tk.Button(reset_frame, text="🗑 Reset Cache คำตอบ", font=theme.FONT_SMALL,
                  bg="#7B1FA2", fg="white", relief="flat", padx=8, pady=4,
                  command=self._reset_cache).pack(side="left")

        # ── Right column ──────────────────────────────────────────────────
        self._grid = EpisodeGrid(
            right,
            self._ep_statuses(self._current_course),
            course_episodes=self._current_course.episodes,
            on_reset_ep=self._reset_episode,
            on_retry_ep=self._retry_episode,
        )
        self._grid.pack(fill="x", pady=(0, 8))

        self._log_panel = LogPanel(right)
        self._log_panel.pack(fill="both", expand=True)
        self._log_panel.set_episode_names(
            [ep.name for ep in self._current_course.episodes])

    # ── Engine callbacks ──────────────────────────────────────────────────────

    def _on_state_change(self, state: AppState) -> None:
        self.after(0, lambda s=state: self._apply_state(s))

    def _apply_state(self, state: AppState) -> None:
        self._ctrl.set_running(state.running)
        self._ctrl.set_status(state.status_text, state.status_color)
        self._ctrl.set_progress(state.completed, state.total)
        self._grid.update_episodes(state.episodes)
        self._timing.update(state.elapsed_seconds, state.eta_seconds)
        self._timing.set_running(state.running)
        self._log_panel.set_logs(state.logs, state.ep_logs)

    # ── Course change ─────────────────────────────────────────────────────────

    def _on_course_change(self, course: CourseConfig) -> None:
        if self._engine and self._engine.is_running:
            messagebox.showwarning("เปลี่ยน Course",
                                   "กรุณาหยุดการทำงานก่อนเปลี่ยน Course")
            return
        self._current_course = course
        self._grid.update_episodes(self._ep_statuses(course))
        self._grid._course_eps = course.episodes
        self._log_panel.set_episode_names([ep.name for ep in course.episodes])
        self._settings.set("last_course", course.course_id)
        self._load_stored_progress()

    def _on_profile_select(self, email: str) -> None:
        self._settings.set("last_profile", email)

    # ── Start / Stop ──────────────────────────────────────────────────────────

    def _start(self, ep_filter=None) -> None:
        if self._engine and self._engine.is_running:
            return
        email    = self._creds.email
        password = self._creds.password
        if not email or not password:
            messagebox.showwarning("Login", "กรุณากรอก Email และ Password")
            return

        self._engine = AutomationEngine(
            course=self._current_course,
            email=email,
            password=password,
            headless=self._opts.headless,
            speed=self._opts.speed,
            data_dir=DATA_DIR,
            on_state_change=self._on_state_change,
            ep_filter=ep_filter,
        )
        self._engine.start()
        self._ctrl.set_running(True)
        self._timing.set_running(True)
        self._settings.save({
            **self._settings.load(),
            "last_profile": email,
            "last_course":  self._current_course.course_id,
        })

    def _stop(self) -> None:
        if self._engine:
            self._engine.stop()

    # ── Test Login ────────────────────────────────────────────────────────────

    def _test_login(self) -> None:
        email    = self._creds.email
        password = self._creds.password
        if not email or not password:
            messagebox.showwarning("Test Login", "กรุณากรอก Email และ Password")
            return
        self._ctrl.set_test_btn_state(False)

        def _run():
            ok = asyncio.run(
                AutomationEngine.test_login(self._current_course, email, password))
            self.after(0, lambda: self._on_login_test_done(ok))

        threading.Thread(target=_run, daemon=True).start()

    def _on_login_test_done(self, ok: bool) -> None:
        self._ctrl.set_test_btn_state(True)
        if ok:
            messagebox.showinfo("Test Login", "✓ Login สำเร็จ!")
        else:
            messagebox.showerror("Test Login", "✗ Login ล้มเหลว\nตรวจสอบ Email / Password")

    # ── Reset / Retry ─────────────────────────────────────────────────────────

    def _reset_episode(self, ep_idx: int) -> None:
        if self._engine and self._engine.is_running:
            messagebox.showwarning("Reset", "หยุดการทำงานก่อน Reset")
            return
        email = self._creds.email
        if not email:
            return
        self._store.reset_episode(email, self._current_course.course_id, ep_idx)
        self._store.clear_answer_cache(
            email, self._current_course.course_id,
            self._current_course.episodes[ep_idx].quiz_post_id)
        self._load_stored_progress()

    def _retry_episode(self, ep_idx: int) -> None:
        if self._engine and self._engine.is_running:
            messagebox.showwarning("Retry", "หยุดการทำงานปัจจุบันก่อน")
            return
        self._start(ep_filter=[ep_idx])

    def _reset_all(self) -> None:
        if self._engine and self._engine.is_running:
            messagebox.showwarning("Reset", "หยุดการทำงานก่อน Reset")
            return
        email = self._creds.email
        if not email:
            messagebox.showwarning("Reset", "เลือก Profile ก่อน")
            return
        if not messagebox.askyesno("Reset ทั้งหมด",
                                   f"ลบ progress ทั้งหมดของ\n{email}\nใน course นี้?"):
            return
        self._store.reset_all(email, self._current_course.course_id)
        self._load_stored_progress()

    def _reset_cache(self) -> None:
        if self._engine and self._engine.is_running:
            messagebox.showwarning("Reset Cache", "หยุดการทำงานก่อน")
            return
        email = self._creds.email
        if not email:
            messagebox.showwarning("Reset Cache", "เลือก Profile ก่อน")
            return
        if not messagebox.askyesno("Reset Cache คำตอบ",
                                   "ล้าง cache คำตอบ quiz ทั้งหมด\n(progress ยังอยู่)"):
            return
        self._store.clear_all_answer_cache(email, self._current_course.course_id)
        messagebox.showinfo("Reset Cache", "ล้าง cache คำตอบเรียบร้อย")

    # ── Dark mode ─────────────────────────────────────────────────────────────

    def _on_dark_mode(self, enabled: bool) -> None:
        messagebox.showinfo("Dark Mode",
                            "Dark Mode จะมีผลหลังรีสตาร์ทโปรแกรม")

    # ── Load stored progress into grid ───────────────────────────────────────

    def _load_stored_progress(self) -> None:
        email = self._creds.email
        if not email:
            self._grid.update_episodes(self._ep_statuses(self._current_course))
            return
        details = self._store.get_all_episode_details(
            email, self._current_course.course_id)
        statuses = self._ep_statuses(self._current_course)
        for idx, d in details.items():
            if idx < len(statuses):
                statuses[idx] = EpisodeStatus(
                    name=self._current_course.episodes[idx].name,
                    status="done" if d.get("complete") else "failed",
                    score=d.get("score"),
                    lesson_ok=d.get("lesson_ok", False),
                    attempts=d.get("attempts", 0),
                    last_ts=d.get("ts", ""),
                )
        self._grid.update_episodes(statuses)
        done = sum(1 for d in details.values() if d.get("complete"))
        self._ctrl.set_progress(done, len(self._current_course.episodes))

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _ep_statuses(course: CourseConfig):
        return [EpisodeStatus(name=ep.name) for ep in course.episodes]

    def _on_close(self) -> None:
        if self._engine and self._engine.is_running:
            if not messagebox.askyesno("ออกจากโปรแกรม",
                                       "กำลังทำงานอยู่ ต้องการออกจริงไหม?"):
                return
            self._engine.stop()
        try:
            self._settings.set("window_geometry", self.geometry())
        except Exception:
            pass
        self.destroy()
