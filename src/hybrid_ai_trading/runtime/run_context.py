# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class RunContext:
    """
    Canonical runtime context shared by:
      - pre-market routines
      - sim/paper/live runners
      - exporters (Notion/CSV)
    """

    as_of_date: str
    mode: str                 # "paper" | "live" | "backtest"
    is_paper: bool            # derived from mode / flags; keep for backward compat
    symbol: str
    regime: str
    repo_root: Path

    # Contract paths (deterministic, env-overridable)
    blockg_status_path: Path

    @staticmethod
    def _repo_root() -> Path:
        # repo_root = .../src/hybrid_ai_trading/runtime/run_context.py -> repo root
        return Path(__file__).resolve().parents[3]

    @staticmethod
    def _resolve_blockg_status_path(repo_root: Path) -> Path:
        p_env = os.environ.get("HAT_BLOCKG_STATUS_PATH", "").strip()
        if p_env:
            return Path(p_env)
        return repo_root / "logs" / "blockg_status_stub.json"

    @staticmethod
    def today(symbol: str, regime: str, is_paper: bool) -> "RunContext":
        """
        Backward-compatible constructor used by older call sites.
        """
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
        """
        Canonical producer. Priority order (fail-safe defaults):
          - mode: explicit arg > env:HAT_MODE > derived from is_paper/env:HAT_IS_PAPER > "paper"
          - as_of_date: explicit arg > env:HAT_AS_OF_DATE > today
        """
        root = repo_root or RunContext._repo_root()

        # date
        d = (as_of_date or os.environ.get("HAT_AS_OF_DATE", "").strip() or date.today().isoformat())
        d = d[:10] if len(d) >= 10 else d

        # mode
        m = (mode or os.environ.get("HAT_MODE", "").strip().lower())
        if m not in ("paper", "live", "backtest"):
            # derive from is_paper or env:HAT_IS_PAPER (default paper-safe)
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
