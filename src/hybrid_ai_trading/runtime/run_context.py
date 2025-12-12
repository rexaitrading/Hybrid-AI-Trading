from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Optional


class RunMode(str, Enum):
    PREMARKET = "premarket"
    PAPER     = "paper"
    LIVE      = "live"
    NOTION    = "notion"


@dataclass(frozen=True)
class RunContext:
    """
    Immutable runtime context for a single system run.

    This object is the *only* authority for:
    - run mode (paper/live/etc.)
    - trading date
    - symbol scope
    - safety readiness snapshots
    """

    mode: RunMode
    trading_date: date

    # scope
    symbol: Optional[str] = None  # NVDA / SPY / QQQ / None (ALL)

    # safety snapshots
    phase4_passed: bool = False
    blockg_ready: bool = False

    # io roots
    repo_root: Path = Path(".")
    logs_dir: Path = Path("logs")

    @property
    def is_live(self) -> bool:
        return self.mode == RunMode.LIVE

    @property
    def is_paper(self) -> bool:
        return self.mode == RunMode.PAPER

    @property
    def is_premarket(self) -> bool:
        return self.mode == RunMode.PREMARKET

    def require_live_safe(self) -> None:
        """
        Hard safety assertion for LIVE mode.
        """
        if not self.is_live:
            return
        if not self.phase4_passed:
            raise RuntimeError("RunContext: Phase-4 not passed for LIVE run")
        if not self.blockg_ready:
            raise RuntimeError("RunContext: Block-G not ready for LIVE run")
