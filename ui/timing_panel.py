import time
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
        self._tick_origin: Optional[float] = None   # monotonic reference
        self._elapsed_at_origin: float = 0.0
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
        was_running = self._running
        self._running = running
        if running and not was_running:
            # Anchor the tick to current wall time
            self._tick_origin = time.monotonic()
            self._elapsed_at_origin = self._elapsed
            self._tick()

    def update(self, elapsed: float, eta: Optional[float]) -> None:
        """Called by engine with authoritative elapsed value — re-sync tick origin."""
        self._elapsed = elapsed
        self._tick_origin = time.monotonic()
        self._elapsed_at_origin = elapsed
        self._eta = eta
        self._elapsed_var.set(_fmt(elapsed))
        self._eta_var.set(_fmt(eta) if eta else "--:--")

    # ── 1-second tick (UI thread only) ────────────────────────────────────────

    def _tick(self) -> None:
        if not self._running:
            return
        if self._tick_origin is not None:
            self._elapsed = self._elapsed_at_origin + (time.monotonic() - self._tick_origin)
        self._elapsed_var.set(_fmt(self._elapsed))
        self.after(1000, self._tick)
