import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

from ui import theme
from utils.profile_store import Profile, ProfileStore


class CredentialsPanel(tk.Frame):
    def __init__(self, master, profile_store: ProfileStore,
                 on_profile_select: Optional[Callable[[str], None]] = None,
                 **kw):
        super().__init__(master, bg=theme.BG(), **kw)
        self._store = profile_store
        self._on_select_cb = on_profile_select
        self._profiles: dict = {}
        self._build()
        self._refresh_profiles()

    def _build(self) -> None:
        self.configure(bg=theme.BG())
        tk.Label(self, text="บัญชีผู้ใช้", font=theme.FONT_BOLD,
                 bg=theme.BG(), fg=theme.TEXT()
                 ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))

        # Profile dropdown
        tk.Label(self, text="โปรไฟล์:", font=theme.FONT_LABEL,
                 bg=theme.BG(), fg=theme.TEXT()
                 ).grid(row=1, column=0, sticky="e", padx=(0, 6))

        self._profile_var = tk.StringVar()
        self._profile_cb = ttk.Combobox(
            self, textvariable=self._profile_var, state="readonly", width=22)
        self._profile_cb.grid(row=1, column=1, sticky="w")
        self._profile_cb.bind("<<ComboboxSelected>>", self._on_profile_select)

        tk.Button(self, text="+ บันทึก", font=theme.FONT_SMALL,
                  command=self._save_profile, relief="flat",
                  bg=theme.PRIMARY(), fg="white", padx=6
                  ).grid(row=1, column=2, padx=4)
        tk.Button(self, text="ลบ", font=theme.FONT_SMALL,
                  command=self._delete_profile, relief="flat",
                  bg=theme.ERROR(), fg="white", padx=6
                  ).grid(row=1, column=3)

        # Email
        tk.Label(self, text="Email:", font=theme.FONT_LABEL,
                 bg=theme.BG(), fg=theme.TEXT()
                 ).grid(row=2, column=0, sticky="e", padx=(0, 6), pady=(6, 0))
        self._email_var = tk.StringVar()
        tk.Entry(self, textvariable=self._email_var, width=32,
                 font=theme.FONT_LABEL, bg=theme.ENTRY_BG(), fg=theme.ENTRY_FG()
                 ).grid(row=2, column=1, columnspan=3, sticky="w", pady=(6, 0))

        # Password
        tk.Label(self, text="Password:", font=theme.FONT_LABEL,
                 bg=theme.BG(), fg=theme.TEXT()
                 ).grid(row=3, column=0, sticky="e", padx=(0, 6), pady=(4, 0))
        self._pass_var = tk.StringVar()
        tk.Entry(self, textvariable=self._pass_var, width=32,
                 show="*", font=theme.FONT_LABEL,
                 bg=theme.ENTRY_BG(), fg=theme.ENTRY_FG()
                 ).grid(row=3, column=1, columnspan=3, sticky="w", pady=(4, 0))

    def _refresh_profiles(self) -> None:
        profiles = self._store.list_profiles()
        names = [p.name for p in profiles]
        self._profile_cb["values"] = names
        self._profiles = {p.name: p for p in profiles}

    def _on_profile_select(self, _=None) -> None:
        name = self._profile_var.get()
        p = self._profiles.get(name)
        if p:
            self._email_var.set(p.email)
            self._pass_var.set(p.password)
            if self._on_select_cb:
                self._on_select_cb(p.email)

    def _save_profile(self) -> None:
        name  = self._profile_var.get().strip()
        email = self._email_var.get().strip()
        pwd   = self._pass_var.get()
        if not name:
            name = email
        if not email or not pwd:
            messagebox.showwarning("บันทึกโปรไฟล์", "กรุณากรอก Email และ Password")
            return
        self._store.save_profile(Profile(name=name, email=email, password=pwd))
        self._refresh_profiles()
        self._profile_var.set(name)

    def _delete_profile(self) -> None:
        name = self._profile_var.get()
        if not name:
            return
        if not messagebox.askyesno("ลบโปรไฟล์", f"ลบ '{name}' ใช่ไหม?"):
            return
        self._store.delete_profile(name)
        self._profile_var.set("")
        self._email_var.set("")
        self._pass_var.set("")
        self._refresh_profiles()

    @property
    def email(self) -> str:
        return self._email_var.get().strip()

    @property
    def password(self) -> str:
        return self._pass_var.get()
