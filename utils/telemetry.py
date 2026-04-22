"""Lightweight append-only JSONL telemetry for automation runs.

Zero external dependencies. Writes one JSON line per event to data/automation.jsonl.
Rotation at 10 MB keeps the file readable without unbounded growth.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_MAX_SIZE = 10 * 1024 * 1024   # 10 MB
_BACKUP_COUNT = 3


def log_event(jsonl_path: Path, event_type: str, **data: Any) -> None:
    """Append one structured JSON line to the telemetry file."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        **data,
    }
    line = json.dumps(entry, separators=(",", ":"), ensure_ascii=False) + "\n"
    try:
        try:
            if jsonl_path.stat().st_size > _MAX_SIZE:
                _rotate(jsonl_path)
        except FileNotFoundError:
            jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with open(jsonl_path, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError as e:
        print(f"[telemetry] write failed: {e}", file=sys.stderr, flush=True)


def _rotate(path: Path) -> None:
    for i in range(_BACKUP_COUNT, 1, -1):
        src = path.with_suffix(f".jsonl.{i - 1}") if i > 1 else path.with_name(path.name + ".1")
        # Use numeric suffixes appended to full filename
        src = Path(str(path) + f".{i - 1}")
        dst = Path(str(path) + f".{i}")
        if src.exists():
            dst.unlink(missing_ok=True)
            src.rename(dst)
    backup = Path(str(path) + ".1")
    backup.unlink(missing_ok=True)
    path.rename(backup)
