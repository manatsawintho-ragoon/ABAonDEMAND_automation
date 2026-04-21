import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from ui import theme


class ControlBar(tk.Frame):
    """Start / Stop / Test-Login buttons + status label + progress bar."""

    def __init__(self, master,
                 on_start: Callable[[], None],
                 on_stop:  Callable[[], None],
                 on_test_login: Optional[Callable[[], None]] = None,
                 **kw):
        super().__init__(master, bg=theme.BG(), **kw)
        self._on_start      = on_start
        self._on_stop       = on_stop
        self._on_test_login = on_test_login
        self._build()

    def _build(self) -> None:
        self.configure(bg=theme.BG())

        btn_frame = tk.Frame(self, bg=theme.BG())
        btn_frame.pack(fill="x")

        self._start_btn = tk.Button(
            btn_frame, text="▶  Start", font=theme.FONT_BOLD,
            bg=theme.SUCCESS(), fg="white", relief="flat",
            padx=18, pady=7, command=self._on_start)
        self._start_btn.pack(side="left", padx=(0, 6))

        self._stop_btn = tk.Button(
            btn_frame, text="■  Stop", font=theme.FONT_BOLD,
            bg=theme.ERROR(), fg="white", relief="flat",
            padx=18, pady=7, command=self._on_stop, state="disabled")
        self._stop_btn.pack(side="left", padx=(0, 6))

        if self._on_test_login:
            self._test_btn = tk.Button(
                btn_frame, text="🔌 Test Login", font=theme.FONT_SMALL,
                bg=theme.WARNING(), fg="white", relief="flat",
                padx=10, pady=7, command=self._on_test_login)
            self._test_btn.pack(side="left", padx=(0, 6))

        self._status_lbl = tk.Label(
            btn_frame, text="พร้อมเริ่มงาน", font=theme.FONT_BOLD,
            bg=theme.BG(), fg=theme.TEXT())
        self._status_lbl.pack(side="left", padx=10)

        # Progress bar
        pb_frame = tk.Frame(self, bg=theme.BG())
        pb_frame.pack(fill="x", pady=(6, 0))

        self._pb = ttk.Progressbar(pb_frame, mode="determinate",
                                   maximum=100, value=0)
        self._pb.pack(fill="x", side="left", expand=True)

        self._pb_lbl = tk.Label(pb_frame, text="0 / 0", font=theme.FONT_SMALL,
                                bg=theme.BG(), fg=theme.TEXT_SUB(), width=8)
        self._pb_lbl.pack(side="left", padx=(6, 0))

    # ── Public ────────────────────────────────────────────────────────────────

    def set_running(self, running: bool) -> None:
        self._start_btn.config(state="disabled" if running else "normal")
        self._stop_btn.config(state="normal"   if running else "disabled")

    def set_status(self, text: str, color: str) -> None:
        self._status_lbl.config(text=text, fg=color)

    def set_progress(self, completed: int, total: int) -> None:
        pct = round(completed / total * 100) if total else 0
        self._pb["value"] = pct
        self._pb_lbl.config(text=f"{completed} / {total}")

    def set_test_btn_state(self, enabled: bool) -> None:
        if hasattr(self, "_test_btn"):
            self._test_btn.config(state="normal" if enabled else "disabled",
                                  text="🔌 Test Login" if enabled else "กำลังตรวจ…")
