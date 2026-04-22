import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from ui import theme
from utils.llm_answerer import FREE_MODELS, DEFAULT_MODEL
from utils.settings_store import SettingsStore

SPEED_OPTIONS = ["fast", "normal", "careful"]

# Display names only (for the combobox)
_MODEL_LABELS = [label for label, _ in FREE_MODELS]
_MODEL_IDS    = {label: mid for label, mid in FREE_MODELS}
_LABEL_BY_ID  = {mid: label for label, mid in FREE_MODELS}


class OptionsPanel(tk.Frame):
    def __init__(self, master, settings: SettingsStore,
                 on_dark_mode: Optional[Callable[[bool], None]] = None,
                 **kw):
        super().__init__(master, bg=theme.BG(), **kw)
        self._settings = settings
        self._on_dark  = on_dark_mode
        self._saved    = settings.load()
        self._build()

    def _build(self) -> None:
        self.configure(bg=theme.BG())
        tk.Label(self, text="ตัวเลือก", font=theme.FONT_BOLD,
                 bg=theme.BG(), fg=theme.TEXT()
                 ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))

        # Headless
        self._headless_var = tk.BooleanVar(value=self._saved.get("headless", False))
        tk.Checkbutton(
            self, text="ซ่อนเบราว์เซอร์",
            variable=self._headless_var,
            font=theme.FONT_LABEL, bg=theme.BG(), fg=theme.TEXT(),
            activebackground=theme.BG(),
            command=self._save,
        ).grid(row=1, column=0, columnspan=2, sticky="w")

        # Speed
        tk.Label(self, text="ความเร็ว:", font=theme.FONT_LABEL,
                 bg=theme.BG(), fg=theme.TEXT()
                 ).grid(row=1, column=2, sticky="e", padx=(12, 4))
        self._speed_var = tk.StringVar(value=self._saved.get("speed", "normal"))
        speed_cb = ttk.Combobox(self, textvariable=self._speed_var,
                                values=SPEED_OPTIONS, state="readonly", width=10)
        speed_cb.grid(row=1, column=3, sticky="w")
        speed_cb.bind("<<ComboboxSelected>>", lambda _: self._save())

        # Dark mode
        self._dark_var = tk.BooleanVar(value=self._saved.get("dark_mode", False))
        tk.Checkbutton(
            self, text="Dark Mode (รีสตาร์ทเพื่อใช้งาน)",
            variable=self._dark_var,
            font=theme.FONT_LABEL, bg=theme.BG(), fg=theme.TEXT(),
            activebackground=theme.BG(),
            command=self._on_dark_toggle,
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))

        # Auto-start
        self._auto_var = tk.BooleanVar(value=self._saved.get("auto_start", False))
        tk.Checkbutton(
            self, text="Auto-start เมื่อเปิดโปรแกรม",
            variable=self._auto_var,
            font=theme.FONT_LABEL, bg=theme.BG(), fg=theme.TEXT(),
            activebackground=theme.BG(),
            command=self._save,
        ).grid(row=2, column=3, sticky="w", pady=(4, 0))

        # ── OpenRouter AI (quiz answering) ────────────────────────────────────
        tk.Label(self, text="OpenRouter Key:", font=theme.FONT_LABEL,
                 bg=theme.BG(), fg=theme.TEXT()
                 ).grid(row=3, column=0, sticky="e", padx=(0, 6), pady=(10, 0))

        # Migrate old anthropic_api_key → openrouter_api_key
        saved_key = (self._saved.get("openrouter_api_key")
                     or self._saved.get("anthropic_api_key", ""))
        self._api_key_var = tk.StringVar(value=saved_key)
        api_entry = tk.Entry(self, textvariable=self._api_key_var, width=30,
                             font=theme.FONT_LABEL,
                             bg=theme.ENTRY_BG(), fg=theme.ENTRY_FG())
        api_entry.grid(row=3, column=1, columnspan=3, sticky="w", pady=(10, 0))
        api_entry.bind("<FocusOut>", lambda _: self._save())

        tk.Label(self, text="AI Model:", font=theme.FONT_LABEL,
                 bg=theme.BG(), fg=theme.TEXT()
                 ).grid(row=4, column=0, sticky="e", padx=(0, 6), pady=(4, 0))

        saved_model_id = self._saved.get("ai_model", DEFAULT_MODEL)
        default_label  = _LABEL_BY_ID.get(saved_model_id, _MODEL_LABELS[0])
        self._model_var = tk.StringVar(value=default_label)
        model_cb = ttk.Combobox(self, textvariable=self._model_var,
                                values=_MODEL_LABELS, state="readonly", width=30)
        model_cb.grid(row=4, column=1, columnspan=3, sticky="w", pady=(4, 0))
        model_cb.bind("<<ComboboxSelected>>", lambda _: self._save())

        tk.Label(self, text="(ตอบ quiz MS Learn อัตโนมัติ — ฟรีทุกโมเดล)",
                 font=theme.FONT_SMALL, bg=theme.BG(), fg=theme.TEXT_SUB()
                 ).grid(row=5, column=1, columnspan=3, sticky="w", pady=(2, 0))

    def _on_dark_toggle(self) -> None:
        self._save()
        if self._on_dark:
            self._on_dark(self._dark_var.get())

    def _save(self) -> None:
        model_id = _MODEL_IDS.get(self._model_var.get(), DEFAULT_MODEL)
        self._settings.save({
            **self._saved,
            "headless":            self._headless_var.get(),
            "speed":               self._speed_var.get(),
            "dark_mode":           self._dark_var.get(),
            "auto_start":          self._auto_var.get(),
            "openrouter_api_key":  self._api_key_var.get(),
            "ai_model":            model_id,
        })

    @property
    def headless(self) -> bool:
        return self._headless_var.get()

    @property
    def speed(self) -> str:
        return self._speed_var.get()

    @property
    def auto_start(self) -> bool:
        return self._auto_var.get()

    @property
    def api_key(self) -> str:
        return self._api_key_var.get().strip()

    @property
    def ai_model(self) -> str:
        return _MODEL_IDS.get(self._model_var.get(), DEFAULT_MODEL)
