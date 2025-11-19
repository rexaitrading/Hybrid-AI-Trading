from __future__ import annotations

from dataclasses import dataclass

from hybrid_ai_trading.risk_config_phase5 import (
    RiskConfigPhase5,
    DailyRiskState,
    SymbolDailyState,
)


@dataclass
class PositionSnapshotStub:
    """Minimal stub of PositionSnapshot for policy tests."""
    unrealized_pnl_bp: float = 0.0


def can_add_position(
    risk_cfg: RiskConfigPhase5,
    pos: PositionSnapshotStub,
    symbol: str,
    daily_state: DailyRiskState,
) -> tuple[bool, str]:
    """Phase 5 risk policy: no averaging down + daily loss caps."""
    # 1) Account-level daily loss caps
    if daily_state.account_pnl_pct <= risk_cfg.daily_loss_cap_pct:
        return False, "daily_loss_cap_pct_reached"

    if daily_state.account_pnl_notional <= risk_cfg.daily_loss_cap_notional:
        return False, "daily_loss_cap_notional_reached"

    # 2) Symbol-level caps
    sym_state = daily_state.by_symbol.get(symbol)
    if sym_state is not None:
        if sym_state.pnl_bp <= risk_cfg.symbol_daily_loss_cap_bp:
            return False, "symbol_daily_loss_cap_reached"
        if sym_state.trades_today >= risk_cfg.symbol_max_trades_per_day:
            return False, "symbol_max_trades_per_day_reached"

    # 3) No averaging down
    if risk_cfg.no_averaging_down:
        if pos.unrealized_pnl_bp <= 0.0:
            return False, "no_averaging_down_block"
        if pos.unrealized_pnl_bp < risk_cfg.min_add_cushion_bp:
            return False, "min_add_cushion_bp_not_met"

    # 4) Position-count / weight caps (using stub DailyRiskState only)
    if daily_state.open_positions >= risk_cfg.max_open_positions:
        return False, "max_open_positions_reached"

    # (symbol_weight_pct is tracked inside SymbolDailyState but we are not
    # exercising it here; we focus on the core caps and no-averaging-down.)

    return True, "okay"


def test_no_averaging_down_blocks_when_unrealized_negative():
    cfg = RiskConfigPhase5()
    pos = PositionSnapshotStub(unrealized_pnl_bp=-5.0)
    daily = DailyRiskState()
    daily.account_pnl_notional = 0.0
    daily.account_pnl_pct = 0.0

    can_add, reason = can_add_position(cfg, pos, "AAPL", daily)
    assert can_add is False
    assert reason == "no_averaging_down_block"


def test_no_averaging_down_blocks_when_unrealized_zero():
    cfg = RiskConfigPhase5()
    pos = PositionSnapshotStub(unrealized_pnl_bp=0.0)
    daily = DailyRiskState()

    can_add, reason = can_add_position(cfg, pos, "AAPL", daily)
    assert can_add is False
    assert reason == "no_averaging_down_block"


def test_min_add_cushion_blocks_when_unrealized_too_small():
    cfg = RiskConfigPhase5(min_add_cushion_bp=3.0)
    pos = PositionSnapshotStub(unrealized_pnl_bp=2.0)
    daily = DailyRiskState()

    can_add, reason = can_add_position(cfg, pos, "AAPL", daily)
    assert can_add is False
    assert reason == "min_add_cushion_bp_not_met"


def test_min_add_cushion_allows_when_unrealized_enough():
    cfg = RiskConfigPhase5(min_add_cushion_bp=3.0)
    pos = PositionSnapshotStub(unrealized_pnl_bp=3.5)
    daily = DailyRiskState()

    can_add, reason = can_add_position(cfg, pos, "AAPL", daily)
    assert can_add is True
    assert reason == "okay"


def test_daily_loss_cap_notional_blocks():
    cfg = RiskConfigPhase5(daily_loss_cap_notional=-1000.0)
    pos = PositionSnapshotStub(unrealized_pnl_bp=10.0)
    daily = DailyRiskState()
    daily.account_pnl_notional = -1500.0  # worse than cap

    can_add, reason = can_add_position(cfg, pos, "AAPL", daily)
    assert can_add is False
    assert reason == "daily_loss_cap_notional_reached"


def test_symbol_loss_cap_bp_blocks():
    cfg = RiskConfigPhase5(symbol_daily_loss_cap_bp=-50.0)
    pos = PositionSnapshotStub(unrealized_pnl_bp=10.0)

    daily = DailyRiskState()
    daily.by_symbol["AAPL"] = SymbolDailyState(pnl_bp=-60.0, pnl_notional=-600.0, trades_today=1)

    can_add, reason = can_add_position(cfg, pos, "AAPL", daily)
    assert can_add is False
    assert reason == "symbol_daily_loss_cap_reached"


def test_symbol_max_trades_blocks():
    cfg = RiskConfigPhase5(symbol_max_trades_per_day=3)
    pos = PositionSnapshotStub(unrealized_pnl_bp=10.0)

    daily = DailyRiskState()
    daily.by_symbol["AAPL"] = SymbolDailyState(pnl_bp=10.0, pnl_notional=100.0, trades_today=3)

    can_add, reason = can_add_position(cfg, pos, "AAPL", daily)
    assert can_add is False
    assert reason == "symbol_max_trades_per_day_reached"


def test_happy_path_no_caps_hit():
    cfg = RiskConfigPhase5(
        daily_loss_cap_pct=-0.02,
        daily_loss_cap_notional=-1000.0,
        symbol_daily_loss_cap_bp=-50.0,
        symbol_max_trades_per_day=3,
        max_open_positions=10,
    )

    pos = PositionSnapshotStub(unrealized_pnl_bp=5.0)  # >= min_add_cushion_bp=3.0
    daily = DailyRiskState()
    daily.account_pnl_notional = 500.0
    daily.account_pnl_pct = 0.01
    daily.open_positions = 2
    daily.by_symbol["AAPL"] = SymbolDailyState(pnl_bp=20.0, pnl_notional=200.0, trades_today=1)

    can_add, reason = can_add_position(cfg, pos, "AAPL", daily)
    assert can_add is True
    assert reason == "okay"