from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional
from pathlib import Path
import os


@dataclass(frozen=True)
class RunContext:
    """
    Unified runtime context for all phases.
    FAIL-CLOSED defaults:
      - is_paper defaults to True unless explicitly set to "0"
      - blockg_status_path defaults to repo logs stub path if provided, else None
    """
    as_of_date: str
    mode: str                 # "paper" | "live" | "backtest"
    is_paper: bool
    symbol: str
    regime: str
    repo_root: Path
    blockg_status_path: Path
    @staticmethod
    def from_env() -> "RunContext":
        # Convenience: preserve older API by producing a full context with safe defaults.
        v = str(os.environ.get("HAT_IS_PAPER", "")).strip()
        m = "live" if v == "0" else "paper"
        return RunContext.from_env_and_args(symbol="NVDA", regime="unknown", mode=m)

        
    @staticmethod
    def _repo_root() -> Path:
        # .../src/hybrid_ai_trading/runtime/run_context.py -> repo root
        return Path(__file__).resolve().parents[3]

    @staticmethod
    def _resolve_blockg_status_path(repo_root: Path) -> Path:
        p_env = os.environ.get("HAT_BLOCKG_STATUS_PATH", "").strip()
        if p_env:
            return Path(p_env)
        return repo_root / "logs" / "blockg_status_stub.json"

    @staticmethod
    def today(symbol: str = "NVDA", regime: str = "unknown", is_paper: bool = True) -> "RunContext":
        root = RunContext._repo_root()
        mode = "paper" if bool(is_paper) else "live"
        return RunContext(
            as_of_date=date.today().isoformat(),
            mode=mode,
            is_paper=bool(is_paper),
            symbol=str(symbol),
            regime=str(regime),
            repo_root=root,
            blockg_status_path=RunContext._resolve_blockg_status_path(root),
        )

    @staticmethod
    def from_env_and_args(
        *,
        symbol: str,
        regime: str,
        mode: Optional[str] = None,
        is_paper: Optional[bool] = None,
        as_of_date: Optional[str] = None,
        repo_root: Optional[Path] = None,
    ) -> "RunContext":
        root = repo_root or RunContext._repo_root()

        d = (as_of_date or os.environ.get("HAT_AS_OF_DATE", "").strip() or date.today().isoformat())
        d = d[:10] if len(d) >= 10 else d

        m = (mode or os.environ.get("HAT_MODE", "").strip().lower())
        if m not in ("paper", "live", "backtest"):
            if is_paper is not None:
                m = "paper" if bool(is_paper) else "live"
            else:
                env_flag = os.environ.get("HAT_IS_PAPER", "").strip()
                m = "live" if env_flag == "0" else "paper"

        paper = (m != "live")

        return RunContext(
            as_of_date=d,
            mode=m,
            is_paper=paper,
            symbol=str(symbol),
            regime=str(regime),
            repo_root=root,
            blockg_status_path=RunContext._resolve_blockg_status_path(root),
        )
