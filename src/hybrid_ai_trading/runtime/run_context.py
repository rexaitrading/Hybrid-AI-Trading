from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path


class RunMode(str, Enum):
    PAPER = "PAPER"
    LIVE = "LIVE"
    PREMARKET = "PREMARKET"


@dataclass(frozen=True)
class RunContext:
    """
    Canonical run context shared across tools/runners/engines.

    Fail-safe defaults:
      - mode defaults to PAPER
      - trading_date defaults to today
      - day_id defaults to ISO date string
    """
    mode: RunMode = RunMode.PAPER
    trading_date: date = date.today()
    symbol: str | None = None

    # legacy compatibility (many modules use day_id)
    day_id: str = ""

    # Phase readiness flags (fail-safe False)
    phase4_passed: bool = False
    blockg_ready: bool = False
    phase23_ok: bool = False
    ev_hard_ok: bool = False
    gatescore_fresh: bool = False

    # repo wiring (safe defaults)
    repo_root: Path = Path(".")
    logs_dir: Path = Path(".") / "logs"
    blockg_path: Path | None = None

    def __post_init__(self):
        # dataclasses(frozen=True) -> use object.__setattr__
        if not self.day_id:
            object.__setattr__(self, "day_id", self.trading_date.isoformat())



    @property
    def is_live(self) -> bool:
        return self.mode == RunMode.LIVE

    @property
    def is_paper(self) -> bool:
        return self.mode == RunMode.PAPER

    @classmethod
    def from_env(cls) -> "RunContext":
        # Delegate to canonical loader (single authority)
        from hybrid_ai_trading.runtime.context_loader import load_run_context_from_env
        return load_run_context_from_env()
__all__ =  ["RunMode", "RunContext"]