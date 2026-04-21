import json
import threading
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List


@dataclass
class Profile:
    name: str     # display label e.g. "Customer A"
    email: str
    password: str # stored as-is (same trust model as local progress file)


class ProfileStore:
    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)

    def list_profiles(self) -> List[Profile]:
        raw = self._load()
        return [Profile(**p) for p in raw]

    def save_profile(self, profile: Profile) -> None:
        with self._lock:
            raw = self._load()
            # update existing email or append
            for p in raw:
                if p["email"] == profile.email:
                    p.update(asdict(profile))
                    break
            else:
                raw.append(asdict(profile))
            self._save(raw)

    def delete_profile(self, name: str) -> None:
        with self._lock:
            raw = [p for p in self._load() if p["name"] != name]
            self._save(raw)

    def _load(self) -> List[dict]:
        try:
            if self._path.exists():
                return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return []

    def _save(self, data: List[dict]) -> None:
        self._path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
