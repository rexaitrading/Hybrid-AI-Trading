from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class SymbolDailyState:
    """Per-symbol daily risk state snapshot."""
    pnl_bp: float = 0.0
    pnl_notional: float = 0.0
    trades_today: int = 0
    symbol_weight_pct: float = 0.0


@dataclass
class DailyRiskState:
    """Account + symbol aggregated daily risk state."""
    account_pnl_bp: float = 0.0
    account_pnl_pct: float = 0.0
    account_pnl_notional: float = 0.0
    open_positions: int = 0
    by_symbol: Dict[str, SymbolDailyState] = field(default_factory=dict)
    loss_cap_hit: bool = False
    loss_cap_hit_reason: Optional[str] = None


@dataclass
class RiskConfigPhase5:
    """
    Configurable Phase 5 risk parameters.

    Intended to be loaded from config/risk_phase5.json and consumed by
    RiskManagerPhase5 / TradeEnginePhase5. Do not hard-code these
    values in the engine; always go through this config layer.
    """

    name: str = "Phase5_Default"

    # === No averaging down ===
    no_averaging_down: bool = True
    min_add_cushion_bp: float = 3.0

    # === Daily loss caps (account level) ===
    daily_loss_cap_pct: float = -0.02
    daily_loss_cap_notional: float = -1000.0

    # === Daily loss caps (symbol level) ===
    symbol_daily_loss_cap_bp: float = -50.0
    symbol_max_trades_per_day: int = 3

    # === Misc position constraints ===
    max_open_positions: int = 10
    max_symbol_weight_pct: float = 0.15

    # === Cooldown after hitting cap ===
    cooldown_minutes_after_loss_cap: int = 60

    # === Logging / telemetry ===
    log_risk_decisions: bool = True
    log_path: str = "logs/risk_pulse_phase5.jsonl"