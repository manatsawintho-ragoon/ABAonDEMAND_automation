import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from typing import Dict, List, Optional

from ui import theme


class LogPanel(tk.Frame):
    """Scrolled log with search, episode filter, and export."""

    def __init__(self, master, **kw):
        super().__init__(master, bg=theme.BG(), **kw)
        self._all_logs: List[str] = []
        self._ep_logs:  Dict[int, List[str]] = {}
        self._ep_names: List[str] = []
        self._build()

    def _build(self) -> None:
        self.configure(bg=theme.BG())

        # ── Toolbar ───────────────────────────────────────────────────────
        bar = tk.Frame(self, bg=theme.BG())
        bar.pack(fill="x", pady=(0, 4))

        tk.Label(bar, text="Log", font=theme.FONT_BOLD,
                 bg=theme.BG(), fg=theme.TEXT()).pack(side="left")

        # Export button
        tk.Button(bar, text="Export", font=theme.FONT_SMALL,
                  command=self._export, relief="flat",
                  bg=theme.PRIMARY(), fg="white", padx=8
                  ).pack(side="right", padx=(4, 0))

        # Search
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        tk.Entry(bar, textvariable=self._search_var, width=18,
                 font=theme.FONT_SMALL, bg=theme.ENTRY_BG(),
                 fg=theme.ENTRY_FG()
                 ).pack(side="right", padx=(4, 0))
        tk.Label(bar, text="🔍", font=theme.FONT_SMALL,
                 bg=theme.BG(), fg=theme.TEXT()).pack(side="right")

        # Episode filter
        self._filter_var = tk.StringVar(value="ทั้งหมด")
        self._ep_cb = ttk.Combobox(bar, textvariable=self._filter_var,
                                   state="readonly", width=18, font=theme.FONT_SMALL)
        self._ep_cb["values"] = ["ทั้งหมด"]
        self._ep_cb.bind("<<ComboboxSelected>>", lambda _: self._apply_filter())
        self._ep_cb.pack(side="right", padx=(4, 0))
        tk.Label(bar, text="Filter:", font=theme.FONT_SMALL,
                 bg=theme.BG(), fg=theme.TEXT()).pack(side="right")

        # ── Text area ─────────────────────────────────────────────────────
        frame = tk.Frame(self, bg=theme.BG())
        frame.pack(fill="both", expand=True)

        self._text = tk.Text(
            frame, font=theme.FONT_MONO,
            bg=theme.LOG_BG(), fg=theme.LOG_FG(),
            wrap="word", state="disabled", relief="flat",
        )
        sb = ttk.Scrollbar(frame, command=self._text.yview)
        self._text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._text.pack(side="left", fill="both", expand=True)

        # Highlight tag for search matches
        self._text.tag_config("match", background="#FFD700", foreground="#000000")

    # ── Public API ────────────────────────────────────────────────────────────

    def set_episode_names(self, names: List[str]) -> None:
        self._ep_names = names
        self._ep_cb["values"] = ["ทั้งหมด"] + names
        self._filter_var.set("ทั้งหมด")

    def set_logs(self, logs: List[str],
                 ep_logs: Optional[Dict[int, List[str]]] = None) -> None:
        self._all_logs = list(logs)
        if ep_logs is not None:
            self._ep_logs = ep_logs
        self._apply_filter()

    # ── Filter + render ───────────────────────────────────────────────────────

    def _apply_filter(self) -> None:
        selected = self._filter_var.get()
        search   = self._search_var.get().strip().lower()

        # Choose source lines
        if selected == "ทั้งหมด":
            lines = self._all_logs
        else:
            try:
                ep_idx = self._ep_names.index(selected)
                lines = self._ep_logs.get(ep_idx, [])
            except ValueError:
                lines = self._all_logs

        # Apply search filter
        if search:
            lines = [l for l in lines if search in l.lower()]

        self._render(lines, search)

    def _render(self, lines: List[str], highlight: str = "") -> None:
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        for line in lines:
            self._text.insert("end", line + "\n")
        self._text.see("end")

        # Highlight search matches
        if highlight:
            self._text.tag_remove("match", "1.0", "end")
            start = "1.0"
            while True:
                pos = self._text.search(highlight, start, nocase=True, stopindex="end")
                if not pos:
                    break
                end = f"{pos}+{len(highlight)}c"
                self._text.tag_add("match", pos, end)
                start = end

        self._text.configure(state="disabled")

    # ── Export ────────────────────────────────────────────────────────────────

    def _export(self) -> None:
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"aba_log_{ts}.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self._all_logs))
            messagebox.showinfo("Export Log", f"บันทึกแล้วที่:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Log", str(e))
