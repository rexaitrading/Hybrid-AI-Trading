"""
Phase 5 risk configuration loader.

Reads environment variables exported by tools/Export-Phase5RiskEnv.ps1 and
exposes them as a typed Phase5RiskConfig dataclass.

This module is deliberately lightweight so it can be imported from:
- risk_manager.py
- trade engine runners (mock/live)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List
import os


@dataclass
class Phase5RiskConfig:
    daily_loss_cap_usd: float
    max_intraday_dd_usd: float
    max_trades_per_day: int
    max_trades_per_symbol: int
    cooldown_minutes_after_big_loss: int
    no_averaging_down: bool
    allowed_strategies: List[str]


def _get_float_env(name: str, default: float) -> float:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _get_int_env(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def load_phase5_risk_from_env() -> Phase5RiskConfig:
    """
    Load Phase5RiskConfig from environment variables.

    Expected env vars (set by tools/Export-Phase5RiskEnv.ps1):
      - PHASE5_DAILY_LOSS_CAP_USD
      - PHASE5_MAX_DRAWDOWN_USD
      - PHASE5_MAX_TRADES_PER_DAY
      - PHASE5_MAX_TRADES_PER_SYMBOL
      - PHASE5_COOLDOWN_MINUTES
      - PHASE5_NO_AVG_DOWN         (\"1\" = True, anything else = False)
      - PHASE5_ALLOWED_STRATEGIES  (comma-separated list)
    """
    daily_loss_cap_usd = _get_float_env("PHASE5_DAILY_LOSS_CAP_USD", 0.0)
    max_intraday_dd_usd = _get_float_env("PHASE5_MAX_DRAWDOWN_USD", 0.0)
    max_trades_per_day = _get_int_env("PHASE5_MAX_TRADES_PER_DAY", 0)
    max_trades_per_symbol = _get_int_env("PHASE5_MAX_TRADES_PER_SYMBOL", 0)
    cooldown_minutes = _get_int_env("PHASE5_COOLDOWN_MINUTES", 0)

    no_avg_down_flag = os.getenv("PHASE5_NO_AVG_DOWN", "0")
    no_averaging_down = no_avg_down_flag == "1"

    allowed_raw = os.getenv("PHASE5_ALLOWED_STRATEGIES", "")
    allowed_strategies = [s.strip() for s in allowed_raw.split(",") if s.strip()]

    return Phase5RiskConfig(
        daily_loss_cap_usd=daily_loss_cap_usd,
        max_intraday_dd_usd=max_intraday_dd_usd,
        max_trades_per_day=max_trades_per_day,
        max_trades_per_symbol=max_trades_per_symbol,
        cooldown_minutes_after_big_loss=cooldown_minutes,
        no_averaging_down=no_averaging_down,
        allowed_strategies=allowed_strategies,
    )