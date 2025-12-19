from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class RunContext:
    as_of_date: str
    is_paper: bool
    symbol: str
    regime: str
    repo_root: Path

    @staticmethod
    def today(symbol: str, regime: str, is_paper: bool) -> "RunContext":
        # repo_root = .../src/hybrid_ai_trading/runtime/run_context.py -> repo root
        root = Path(__file__).resolve().parents[3]
        return RunContext(
            as_of_date=date.today().isoformat(),
            is_paper=bool(is_paper),
            symbol=str(symbol),
            regime=str(regime),
            repo_root=root,
        )