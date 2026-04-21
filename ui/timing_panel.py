import tkinter as tk
from typing import Optional

from ui import theme


def _fmt(seconds: Optional[float]) -> str:
    if seconds is None:
        return "--:--"
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


class TimingPanel(tk.Frame):
    """Shows elapsed and ETA. Ticks elapsed every second when running."""

    def __init__(self, master, **kw):
        super().__init__(master, bg=theme.BG(), **kw)
        self._running = False
        self._elapsed = 0.0
        self._eta: Optional[float] = None
        self._build()

    def _build(self) -> None:
        self.configure(bg=theme.BG())
        for label_text, attr in [("Elapsed", "_elapsed_var"), ("ETA", "_eta_var")]:
            col = tk.Frame(self, bg=theme.BG(), padx=14)
            col.pack(side="left")
            tk.Label(col, text=label_text, font=theme.FONT_SMALL,
                     bg=theme.BG(), fg=theme.TEXT_SUB()).pack()
            var = tk.StringVar(value="00:00")
            setattr(self, attr, var)
            tk.Label(col, textvariable=var, font=theme.FONT_BOLD,
                     bg=theme.BG(), fg=theme.TEXT()).pack()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_running(self, running: bool) -> None:
        self._running = running
        if running:
            self._tick()

    def update(self, elapsed: float, eta: Optional[float]) -> None:
        self._elapsed = elapsed
        self._eta     = eta
        self._elapsed_var.set(_fmt(elapsed))
        self._eta_var.set(_fmt(eta))

    # ── 1-second tick ─────────────────────────────────────────────────────────

    def _tick(self) -> None:
        if not self._running:
            return
        self._elapsed += 1.0
        self._elapsed_var.set(_fmt(self._elapsed))
        self.after(1000, self._tick)
