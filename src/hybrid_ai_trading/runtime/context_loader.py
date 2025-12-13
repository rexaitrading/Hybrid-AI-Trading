from __future__ import annotations

import os
from datetime import date, datetime

from hybrid_ai_trading.runtime.run_context import RunContext, RunMode


def _norm_mode(s: str) -> str:
    return (s or "").strip().lower()


def _env_trading_date() -> date:
    """
    trading_date authority:
      1) HAT_TRADING_DATE=YYYY-MM-DD (optional override)
      2) date.today() (default)
    """
    raw = (os.getenv("HAT_TRADING_DATE", "") or "").strip()
    if raw:
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except Exception:
            pass
    return date.today()


def load_run_context_from_env() -> RunContext:
    """
    Canonical RunContext loader (fail-safe default = PAPER).

    Precedence:
      1) HAT_RUN_MODE
      2) HAT_MODE
      3) default: paper

    Accepted: live, paper, premarket
    """
    m = _norm_mode(os.getenv("HAT_RUN_MODE", ""))
    if not m:
        m = _norm_mode(os.getenv("HAT_MODE", ""))

    if m == "live":
        mode = RunMode.LIVE
    elif m == "premarket":
        mode = RunMode.PREMARKET
    else:
        mode = RunMode.PAPER

    return RunContext(mode=mode, trading_date=_env_trading_date())


def is_live_env() -> bool:
    """
    Legacy-friendly check: True only when env resolves to LIVE.
    """
    return load_run_context_from_env().is_live
