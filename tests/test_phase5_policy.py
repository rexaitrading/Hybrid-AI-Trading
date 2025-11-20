"""
Tests for Phase 5 risk policy helpers.

These exercise the pure functions:
  - phase5_can_add_position (RiskConfigPhase5 + DailyRiskState + PnL inputs)

Run with:
  $env:PYTHONPATH = (Resolve-Path "src")
  .\\.venv\\Scripts\\python.exe -m pytest tests/test_phase5_policy.py
"""

from __future__ import annotations

from hybrid_ai_trading.risk.risk_manager import phase5_can_add_position
from hybrid_ai_trading.risk_config_phase5 import (
    RiskConfigPhase5,
    DailyRiskState,
    SymbolDailyState,
)


def _daily_state_for(
    symbol: str,
    account_pnl_pct: float = 0.0,
    account_pnl_notional: float = 0.0,
    open_positions: int = 1,
    symbol_pnl_bp: float = 0.0,
    trades_today: int = 1,
) -> DailyRiskState:
    ds = DailyRiskState()
    ds.account_pnl_pct = account_pnl_pct
    ds.account_pnl_notional = account_pnl_notional
    ds.open_positions = open_positions
    ds.by_symbol[symbol] = SymbolDailyState(
        pnl_bp=symbol_pnl_bp,
        pnl_notional=0.0,
        trades_today=trades_today,
    )
    return ds


def test_phase5_blocks_averaging_down_on_loss():
    cfg = RiskConfigPhase5()
    symbol = "NVDA"
    daily = _daily_state_for(symbol, symbol_pnl_bp=-5.0)

    allow, reason = phase5_can_add_position(
        cfg,
        symbol=symbol,
        pos_unrealized_pnl_bp=-5.0,
        daily_state=daily,
    )

    assert allow is False
    assert reason == "no_averaging_down_block"


def test_phase5_allows_add_when_above_cushion_and_no_caps_hit():
    cfg = RiskConfigPhase5()
    symbol = "NVDA"
    # Winning day, above cushion, no caps hit
    daily = _daily_state_for(symbol, symbol_pnl_bp=20.0)

    allow, reason = phase5_can_add_position(
        cfg,
        symbol=symbol,
        pos_unrealized_pnl_bp=cfg.min_add_cushion_bp + 1.0,
        daily_state=daily,
    )

    assert allow is True
    assert reason == "okay"