from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path
import os


class RunMode(str, Enum):
    REPLAY = "REPLAY"
    PAPER = "PAPER"
    LIVE = "LIVE"


@dataclass(frozen=True)
class RunContext:
    """
    Unified runtime context (single truth) shared by:
      - pre-market routines
      - sim/paper runners
      - live runners
      - Notion exporters

    Fail-closed:
      - LIVE requires a valid Block-G contract for the symbol/day.
    """
    mode: RunMode
    day_id: str
    fail_closed: bool = True
    blockg_path: Path | None = None

    @staticmethod
    def today_day_id() -> str:
        return date.today().isoformat()

    @classmethod
    def from_env(cls) -> "RunContext":
        mode_s = (os.getenv("HAT_RUN_MODE", "PAPER") or "PAPER").strip().upper()
        try:
            mode = RunMode(mode_s)
        except Exception:
            mode = RunMode.PAPER

        day_id = (os.getenv("HAT_DAY_ID", "") or cls.today_day_id()).strip()
        fail_closed = (os.getenv("HAT_FAIL_CLOSED", "1").strip() != "0")
        bg = (os.getenv("HAT_BLOCKG_PATH", "") or "").strip()
        blockg_path = Path(bg) if bg else None
        return cls(mode=mode, day_id=day_id, fail_closed=fail_closed, blockg_path=blockg_path)