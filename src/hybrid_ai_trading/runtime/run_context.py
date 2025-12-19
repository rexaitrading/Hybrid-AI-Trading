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
        root = Path(__file__).resolve().parents[3]
        return RunContext(
            as_of_date=date.today().isoformat(),
            is_paper=is_paper,
            symbol=symbol,
            regime=regime,
            repo_root=root,
        )