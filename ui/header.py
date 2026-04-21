import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict

from courses.base_course import CourseConfig
from ui import theme


class Header(tk.Frame):
    def __init__(self, master,
                 courses: Dict[str, CourseConfig],
                 on_course_change: Callable[[CourseConfig], None],
                 **kw):
        super().__init__(master, bg=theme.HEADER_BG(), **kw)
        self._courses   = courses
        self._on_change = on_course_change
        self._name_map  = {c.display_name: c for c in courses.values()}
        self._build()

    def _build(self) -> None:
        self.configure(bg=theme.HEADER_BG())
        tk.Label(
            self, text="ABA on Demand Automator",
            font=theme.FONT_TITLE, bg=theme.HEADER_BG(), fg=theme.HEADER_FG(),
        ).pack(side="left", padx=16, pady=10)

        right = tk.Frame(self, bg=theme.HEADER_BG())
        right.pack(side="right", padx=12)

        tk.Label(right, text="Course:", font=theme.FONT_LABEL,
                 bg=theme.HEADER_BG(), fg=theme.HEADER_FG()
                 ).pack(side="left", padx=(0, 6))

        names = [c.display_name for c in self._courses.values()]
        self._course_var = tk.StringVar(value=names[0] if names else "")
        cb = ttk.Combobox(right, textvariable=self._course_var,
                          values=names, state="readonly", width=38)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", self._on_select)

    def _on_select(self, _=None) -> None:
        course = self._name_map.get(self._course_var.get())
        if course:
            self._on_change(course)

    @property
    def selected_course(self) -> CourseConfig:
        return self._name_map[self._course_var.get()]
