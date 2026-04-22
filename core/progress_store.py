import json
import os
import threading
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Set


class ProgressStore:
    """Thread-safe, atomic read/write of progress.json.

    Schema:
    {
      "email": {
        "COURSE_ID": {
          "episodes": {
            "0": { "score": 100, "complete": true, "lesson_ok": true,
                   "ep": "Ep 1...", "ts": "...", "attempts": 3 }
          },
          "answer_cache": {
            "44211": { "What does X mean?": "option text A", ... }
          }
        }
      }
    }

    answer_cache values:
      str   → radio question correct option text
      list  → checkbox question correct option texts
    """

    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)

    # ── Episode completion ─────────────────────────────────────────────────

    def get_done_episodes(self, email: str, course_id: str,
                          min_score: int = 100,
                          require_ms_confirmed: bool = False) -> Set[int]:
        """Return episode indices that are complete and meet score threshold.

        If require_ms_confirmed=True (used by MSLearnEngine), episodes that were
        completed but never got explicit 'Module assessment passed' confirmation
        are excluded so the engine re-runs them and obtains the profile badge.
        """
        eps = self._course_data(email, course_id).get("episodes", {})
        result = set()
        for k, v in eps.items():
            if not (v.get("complete") and v.get("score", 0) >= min_score):
                continue
            if require_ms_confirmed and not v.get("ms_confirmed", False):
                continue
            result.add(int(k))
        return result

    def get_all_episode_details(self, email: str, course_id: str) -> Dict[int, dict]:
        """Returns {ep_idx: {score, complete, lesson_ok, ep, ts, attempts}}"""
        eps = self._course_data(email, course_id).get("episodes", {})
        return {int(k): v for k, v in eps.items()}

    def mark_episode(self, email: str, course_id: str,
                     ep_idx: int, ep_name: str, score: int,
                     lesson_ok: bool = False,
                     attempts: int = 0,
                     min_score: int = 100,
                     ms_confirmed: bool = False) -> None:
        with self._lock:
            data = self._load()
            bucket = data.setdefault(email, {}).setdefault(course_id, {})
            bucket.setdefault("episodes", {})[str(ep_idx)] = {
                "score": score,
                "complete": score >= min_score,
                "lesson_ok": lesson_ok,
                "ep": ep_name,
                "ts": datetime.now().isoformat(timespec="seconds"),
                "attempts": attempts,
                "ms_confirmed": ms_confirmed,
            }
            self._atomic_save(data)

    def reset_episode(self, email: str, course_id: str, ep_idx: int) -> None:
        """Remove one episode's progress AND its answer cache."""
        with self._lock:
            data = self._load()
            cd = data.get(email, {}).get(course_id, {})
            cd.get("episodes", {}).pop(str(ep_idx), None)
            self._atomic_save(data)

    def reset_all(self, email: str, course_id: str) -> None:
        """Wipe all progress (episodes + answer cache) for this account+course."""
        with self._lock:
            data = self._load()
            data.get(email, {}).pop(course_id, None)
            self._atomic_save(data)

    # ── Answer cache ───────────────────────────────────────────────────────

    def get_answer_cache(self, email: str, course_id: str,
                         quiz_post_id: int) -> Dict[str, Any]:
        """Returns {question_text: correct_option_text_or_list}.
        Integer-keyed legacy entries (old format) are silently dropped.
        """
        raw = (self._course_data(email, course_id)
               .get("answer_cache", {})
               .get(str(quiz_post_id), {}))
        return {
            k: v for k, v in raw.items()
            if not k.isdigit()          # drop legacy integer-key entries
        }

    def save_answer_cache(self, email: str, course_id: str,
                          quiz_post_id: int, cache: Dict[str, Any]) -> None:
        with self._lock:
            data = self._load()
            bucket = data.setdefault(email, {}).setdefault(course_id, {})
            bucket.setdefault("answer_cache", {})[str(quiz_post_id)] = dict(cache)
            self._atomic_save(data)

    def clear_answer_cache(self, email: str, course_id: str,
                           quiz_post_id: int) -> None:
        with self._lock:
            data = self._load()
            (data.get(email, {})
                 .get(course_id, {})
                 .get("answer_cache", {})
                 .pop(str(quiz_post_id), None))
            self._atomic_save(data)

    def clear_all_answer_cache(self, email: str, course_id: str) -> None:
        with self._lock:
            data = self._load()
            cd = data.get(email, {}).get(course_id, {})
            cd.pop("answer_cache", None)
            self._atomic_save(data)

    # ── Internal ───────────────────────────────────────────────────────────

    def _course_data(self, email: str, course_id: str) -> dict:
        return self._load().get(email, {}).get(course_id, {})

    def _load(self) -> dict:
        try:
            if self._path.exists():
                return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _atomic_save(self, data: dict) -> None:
        """Write to a temp file then rename — prevents corruption on crash."""
        tmp = self._path.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            os.replace(tmp, self._path)
        except Exception:
            tmp.unlink(missing_ok=True)
