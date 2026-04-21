import tkinter as tk
from tkinter import messagebox
import webbrowser
from typing import Callable, List, Optional

from core.state import EpisodeStatus
from ui import theme


class EpisodeGrid(tk.Frame):
    """Color-coded episode grid with tooltip, click-popup, and context menu."""

    COLS = 5

    def __init__(self, master,
                 episodes: List[EpisodeStatus],
                 course_episodes=None,       # List[EpisodeConfig] for URLs
                 on_reset_ep: Optional[Callable[[int], None]] = None,
                 on_retry_ep: Optional[Callable[[int], None]] = None,
                 **kw):
        super().__init__(master, bg=theme.BG(), **kw)
        self._course_eps = course_episodes or []
        self._on_reset   = on_reset_ep
        self._on_retry   = on_retry_ep
        self._cells: list[tk.Label] = []
        self._tip: Optional[tk.Toplevel] = None
        self._build(episodes)

    # ── Build / rebuild ───────────────────────────────────────────────────────

    def _build(self, episodes: List[EpisodeStatus]) -> None:
        for w in self.winfo_children():
            w.destroy()
        self._cells.clear()
        self.configure(bg=theme.BG())

        for i, ep in enumerate(episodes):
            row, col = divmod(i, self.COLS)
            cell = tk.Label(
                self,
                text=self._cell_text(ep),
                bg=self._cell_color(ep),
                fg="white",
                font=theme.FONT_SMALL,
                width=16, height=3,
                relief="flat",
                anchor="center",
                justify="center",
                cursor="hand2",
            )
            cell.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")
            cell.bind("<Button-1>",         lambda e, idx=i: self._on_click(idx))
            cell.bind("<Button-3>",         lambda e, idx=i: self._context_menu(e, idx))
            cell.bind("<Enter>",            lambda e, idx=i: self._show_tip(e, idx))
            cell.bind("<Leave>",            lambda e: self._hide_tip())
            self._cells.append(cell)

        for c in range(self.COLS):
            self.columnconfigure(c, weight=1)

    def update_episodes(self, episodes: List[EpisodeStatus]) -> None:
        if len(episodes) != len(self._cells):
            self._build(episodes)
            return
        for cell, ep in zip(self._cells, episodes):
            cell.config(text=self._cell_text(ep), bg=self._cell_color(ep))

    # ── Click → detail popup ──────────────────────────────────────────────────

    def _on_click(self, idx: int) -> None:
        if idx >= len(self._cells):
            return
        ep = self._get_ep_status(idx)
        if not ep:
            return

        win = tk.Toplevel(self)
        win.title(f"Episode {idx+1} รายละเอียด")
        win.configure(bg=theme.BG())
        win.resizable(False, False)
        win.grab_set()

        rows = [
            ("ชื่อ",         ep.name),
            ("สถานะ",        ep.status),
            ("คะแนน quiz",   f"{ep.score}%" if ep.score is not None else "ยังไม่ได้ทำ"),
            ("Lesson",       "✓ สำเร็จ" if ep.lesson_ok else "✗ ยังไม่สำเร็จ"),
            ("Attempts",     str(ep.attempts) if ep.attempts else "-"),
            ("ครั้งล่าสุด",   ep.last_ts or "-"),
        ]
        for r, (label, val) in enumerate(rows):
            tk.Label(win, text=label + ":", font=theme.FONT_BOLD,
                     bg=theme.BG(), fg=theme.TEXT(), anchor="e", width=14
                     ).grid(row=r, column=0, sticky="e", padx=(12, 4), pady=3)
            tk.Label(win, text=val, font=theme.FONT_LABEL,
                     bg=theme.BG(), fg=theme.TEXT(), anchor="w"
                     ).grid(row=r, column=1, sticky="w", padx=(0, 12), pady=3)

        btn_row = len(rows)
        if self._on_retry:
            tk.Button(win, text="▶ Retry", font=theme.FONT_SMALL,
                      bg=theme.PRIMARY(), fg="white", relief="flat",
                      padx=10, pady=4,
                      command=lambda: (win.destroy(), self._on_retry(idx))
                      ).grid(row=btn_row, column=0, padx=8, pady=10)

        if self._on_reset:
            tk.Button(win, text="🗑 Reset", font=theme.FONT_SMALL,
                      bg=theme.ERROR(), fg="white", relief="flat",
                      padx=10, pady=4,
                      command=lambda: self._confirm_reset(win, idx)
                      ).grid(row=btn_row, column=1, padx=8, pady=10)

        url = self._quiz_url(idx)
        if url:
            tk.Button(win, text="🔗 เปิด Quiz", font=theme.FONT_SMALL,
                      bg=theme.WARNING(), fg="white", relief="flat",
                      padx=10, pady=4,
                      command=lambda: webbrowser.open(url)
                      ).grid(row=btn_row+1, column=0, columnspan=2, pady=(0, 10))

    def _confirm_reset(self, win: tk.Toplevel, idx: int) -> None:
        ep = self._get_ep_status(idx)
        name = ep.name if ep else f"Episode {idx+1}"
        if messagebox.askyesno("Reset Progress",
                               f"ลบ progress + cache คำตอบของ\n'{name}'\nใช่ไหม?",
                               parent=win):
            win.destroy()
            if self._on_reset:
                self._on_reset(idx)

    # ── Right-click context menu ──────────────────────────────────────────────

    def _context_menu(self, event: tk.Event, idx: int) -> None:
        menu = tk.Menu(self, tearoff=0, bg=theme.CARD(), fg=theme.TEXT())
        url = self._quiz_url(idx)
        if url:
            menu.add_command(label="🔗 เปิด Quiz URL",
                             command=lambda: webbrowser.open(url))
        if self._on_retry:
            menu.add_command(label="▶ Retry episode นี้",
                             command=lambda: self._on_retry(idx))
        if self._on_reset:
            menu.add_command(label="🗑 Reset progress",
                             command=lambda: self._on_reset and
                                           self._confirm_reset(None, idx))
        menu.add_separator()
        menu.add_command(label="ℹ รายละเอียด",
                         command=lambda: self._on_click(idx))
        menu.post(event.x_root, event.y_root)

    # ── Tooltip ───────────────────────────────────────────────────────────────

    def _show_tip(self, event: tk.Event, idx: int) -> None:
        self._hide_tip()
        ep = self._get_ep_status(idx)
        if not ep:
            return
        tip_text = (
            f"{ep.name}\n"
            f"สถานะ: {ep.status}\n"
            f"คะแนน: {ep.score}%" if ep.score is not None else f"{ep.name}\nสถานะ: {ep.status}"
        )
        if ep.last_ts:
            tip_text += f"\nล่าสุด: {ep.last_ts}"
        if ep.attempts:
            tip_text += f"\nAttempts: {ep.attempts}"

        self._tip = tk.Toplevel(self)
        self._tip.wm_overrideredirect(True)
        self._tip.configure(bg="#FFFFE0")
        tk.Label(self._tip, text=tip_text, font=theme.FONT_SMALL,
                 bg="#FFFFE0", fg="#333333", relief="solid", borderwidth=1,
                 justify="left", padx=6, pady=4).pack()
        x = event.x_root + 12
        y = event.y_root + 12
        self._tip.geometry(f"+{x}+{y}")

    def _hide_tip(self) -> None:
        if self._tip:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_ep_status(self, idx: int) -> Optional[EpisodeStatus]:
        if idx < len(self._cells):
            # Reconstruct from cell text is impractical; store episodes separately
            return getattr(self, "_episodes", [None] * (idx + 1))[idx]
        return None

    def _quiz_url(self, idx: int) -> str:
        if self._course_eps and idx < len(self._course_eps):
            return self._course_eps[idx].quiz_url
        return ""

    def _store_episodes(self, episodes: List[EpisodeStatus]) -> None:
        self._episodes = list(episodes)

    def _build(self, episodes: List[EpisodeStatus]) -> None:
        self._store_episodes(episodes)
        for w in self.winfo_children():
            w.destroy()
        self._cells.clear()
        self.configure(bg=theme.BG())

        for i, ep in enumerate(episodes):
            row, col = divmod(i, self.COLS)
            cell = tk.Label(
                self,
                text=self._cell_text(ep),
                bg=self._cell_color(ep),
                fg="white",
                font=theme.FONT_SMALL,
                width=16, height=3,
                relief="flat",
                anchor="center",
                justify="center",
                cursor="hand2",
            )
            cell.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")
            cell.bind("<Button-1>",  lambda e, idx=i: self._on_click(idx))
            cell.bind("<Button-3>",  lambda e, idx=i: self._context_menu(e, idx))
            cell.bind("<Enter>",     lambda e, idx=i: self._show_tip(e, idx))
            cell.bind("<Leave>",     lambda e: self._hide_tip())
            self._cells.append(cell)

        for c in range(self.COLS):
            self.columnconfigure(c, weight=1)

    def update_episodes(self, episodes: List[EpisodeStatus]) -> None:
        self._store_episodes(episodes)
        if len(episodes) != len(self._cells):
            self._build(episodes)
            return
        for cell, ep in zip(self._cells, episodes):
            cell.config(text=self._cell_text(ep), bg=self._cell_color(ep))

    @staticmethod
    def _cell_text(ep: EpisodeStatus) -> str:
        icon  = theme.STATUS_ICONS.get(ep.status, "○")
        score = f"{ep.score}%" if ep.score is not None else ""
        name  = ep.name[:15] + "…" if len(ep.name) > 16 else ep.name
        return f"{icon} {name}\n{score}"

    @staticmethod
    def _cell_color(ep: EpisodeStatus) -> str:
        return theme.STATUS_COLORS.get(ep.status, theme.PENDING())
