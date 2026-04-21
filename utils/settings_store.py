import json
import threading
from pathlib import Path
from typing import Any

_DEFAULTS = {
    "headless": False,
    "speed": "normal",
    "dark_mode": False,
    "last_profile": "",
    "last_course": "",
    "auto_start": False,
    "window_geometry": "",
}


class SettingsStore:
    """Persist user preferences between sessions."""

    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                return {**_DEFAULTS, **data}
        except Exception:
            pass
        return dict(_DEFAULTS)

    def save(self, settings: dict) -> None:
        with self._lock:
            try:
                merged = {**_DEFAULTS, **settings}
                self._path.write_text(
                    json.dumps(merged, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            except Exception:
                pass

    def get(self, key: str, default: Any = None) -> Any:
        return self.load().get(key, default)

    def set(self, key: str, value: Any) -> None:
        data = self.load()
        data[key] = value
        self.save(data)
