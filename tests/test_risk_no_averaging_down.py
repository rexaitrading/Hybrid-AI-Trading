import math

from hybrid_ai_trading.risk_no_averaging_down import (
    CostConfig,
    RiskConfig,
    compute_total_cost_bp,
    can_add_to_position,
)


def _approx(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) <= tol


def test_compute_total_cost_bp_zero_notional_returns_zero() -> None:
    cfg = CostConfig(slippage_bp=1.0, fee_bp=0.3, fee_per_share=0.004)
    assert compute_total_cost_bp(cfg, notional=0.0, share_qty_round_trip=100) == 0.0
    assert compute_total_cost_bp(cfg, notional=10_000.0, share_qty_round_trip=0) == 0.0


def test_compute_total_cost_bp_positive_notional() -> None:
    cfg = CostConfig(slippage_bp=1.0, fee_bp=0.3, fee_per_share=0.004)
    notional = 10_000.0
    shares = 100
    cost_bp = compute_total_cost_bp(cfg, notional=notional, share_qty_round_trip=shares)
    # Basic sanity: cost should be > slippage_bp + fee_bp due to per-share fee
    assert cost_bp > cfg.slippage_bp + cfg.fee_bp
    # and not something absurdly large
    assert cost_bp < 50.0


def test_no_averaging_down_blocks_losers() -> None:
    risk_cfg = RiskConfig(no_averaging_down=True, min_add_cushion_bp=3.0)
    cost_cfg = CostConfig(slippage_bp=1.0, fee_bp=0.3, fee_per_share=0.004)

    allowed = can_add_to_position(
        side="LONG",
        position_unrealized_pnl_bp=-5.0,
        existing_notional=10_000.0,
        additional_notional=5_000.0,
        additional_shares_round_trip=100,
        risk_cfg=risk_cfg,
        cost_cfg=cost_cfg,
    )
    assert allowed is False


def test_unknown_side_blocks_conservatively() -> None:
    risk_cfg = RiskConfig(no_averaging_down=True, min_add_cushion_bp=3.0)
    cost_cfg = CostConfig(slippage_bp=1.0, fee_bp=0.3, fee_per_share=0.004)

    allowed = can_add_to_position(
        side="FLAT",
        position_unrealized_pnl_bp=10.0,
        existing_notional=10_000.0,
        additional_notional=5_000.0,
        additional_shares_round_trip=100,
        risk_cfg=risk_cfg,
        cost_cfg=cost_cfg,
    )
    assert allowed is False


def test_small_win_below_cost_plus_cushion_blocks() -> None:
    risk_cfg = RiskConfig(no_averaging_down=True, min_add_cushion_bp=3.0)
    cost_cfg = CostConfig(slippage_bp=1.0, fee_bp=0.3, fee_per_share=0.004)

    # Compute approximate total cost bp for a typical add
    notional = 10_000.0 + 5_000.0
    shares = 100
    total_cost_bp = compute_total_cost_bp(cost_cfg, notional=notional, share_qty_round_trip=shares)
    min_add_pnl_bp = total_cost_bp + risk_cfg.min_add_cushion_bp

    # Choose unrealized PnL slightly BELOW threshold
    unrealized_pnl_bp = min_add_pnl_bp - 0.5

    allowed = can_add_to_position(
        side="LONG",
        position_unrealized_pnl_bp=unrealized_pnl_bp,
        existing_notional=10_000.0,
        additional_notional=5_000.0,
        additional_shares_round_trip=shares,
        risk_cfg=risk_cfg,
        cost_cfg=cost_cfg,
    )
    assert allowed is False


def test_solid_win_above_cost_plus_cushion_allows_add() -> None:
    risk_cfg = RiskConfig(no_averaging_down=True, min_add_cushion_bp=3.0)
    cost_cfg = CostConfig(slippage_bp=1.0, fee_bp=0.3, fee_per_share=0.004)

    notional = 10_000.0 + 5_000.0
    shares = 100
    total_cost_bp = compute_total_cost_bp(cost_cfg, notional=notional, share_qty_round_trip=shares)
    min_add_pnl_bp = total_cost_bp + risk_cfg.min_add_cushion_bp

    # Choose unrealized PnL comfortably ABOVE threshold
    unrealized_pnl_bp = min_add_pnl_bp + 2.0

    allowed = can_add_to_position(
        side="LONG",
        position_unrealized_pnl_bp=unrealized_pnl_bp,
        existing_notional=10_000.0,
        additional_notional=5_000.0,
        additional_shares_round_trip=shares,
        risk_cfg=risk_cfg,
        cost_cfg=cost_cfg,
    )
    assert allowed is True