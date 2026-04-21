from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional


EpStatus = Literal["pending", "running", "done", "failed"]


@dataclass
class EpisodeStatus:
    name: str
    status: EpStatus = "pending"
    score: Optional[int] = None      # 0-100 quiz score, None = not attempted
    lesson_ok: bool = False          # lesson mark-complete succeeded
    attempts: int = 0                # quiz attempt count this session
    last_ts: str = ""                # ISO timestamp of last completion


@dataclass
class AppState:
    episodes: List[EpisodeStatus] = field(default_factory=list)
    current_ep_idx: int = -1
    completed: int = 0
    total: int = 0
    status_text: str = "พร้อมเริ่มงาน"
    status_color: str = "#212121"
    elapsed_seconds: float = 0.0
    eta_seconds: Optional[float] = None
    running: bool = False
    logs: List[str] = field(default_factory=list)
    ep_logs: Dict[int, List[str]] = field(default_factory=dict)  # per-episode logs
