from tools.orb_vwap_gatescore_filter import filter_trades
from hybrid_ai_trading.trade_engine_phase5_skeleton import TradeEnginePhase5
from hybrid_ai_trading.risk_manager_phase5_bridge import PositionSnapshot, AddRequest


def test_phase5_wiring_sim_allows_strong_winner_blocks_flat() -> None:
    # Thresholds similar to orb_vwap_aapl_thresholds.json
    thresholds = {
        "gatescore_edge_ratio_min": 0.04,
        "max_cost_bp": 3.0,
        "min_pnl_pct_training": -0.01,
    }

    # Two synthetic trades:
    #  1) Strong winner -> should pass filter AND gate
    #  2) Flat trade   -> filter passes, but Phase 5 should block add
    trades = [
        {
            "symbol": "AAPL",
            "gatescore_edge_ratio": 0.045,
            "cost_bp": 2.5,
            "pnl_pct": 0.003,   # 30 bp
            "cost_notional": 10_000.0,
        },
        {
            "symbol": "AAPL",
            "gatescore_edge_ratio": 0.045,
            "cost_bp": 2.5,
            "pnl_pct": 0.0,     # flat
            "cost_notional": 10_000.0,
        },
    ]

    gated = filter_trades(trades, thresholds)
    assert len(gated) == 2

    engine = TradeEnginePhase5()
    # Force stable configs
    engine.risk_manager.risk_cfg.no_averaging_down = True
    engine.risk_manager.risk_cfg.min_add_cushion_bp = 3.0

    current_notional = 0.0
    decisions = []

    for t in gated:
        pnl_pct = float(t["pnl_pct"])
        unrealized_pnl_bp = pnl_pct * 10_000.0
        base_notional = float(t["cost_notional"])

        if current_notional == 0.0:
            current_notional = base_notional

        pos = PositionSnapshot(
            symbol=t["symbol"],
            side="LONG",
            unrealized_pnl_bp=unrealized_pnl_bp,
            notional=current_notional,
        )
        add_req = AddRequest(
            additional_notional=base_notional,
            additional_shares_round_trip=100,
        )

        decision = engine.consider_add(pos, add_req)
        decisions.append(decision)

        if decision.can_add:
            current_notional += base_notional

    # Strong winner should be allowed
    assert decisions[0].can_add is True
    assert decisions[0].reason == "okay"

    # Flat trade should be blocked by no_averaging_down
    assert decisions[1].can_add is False
    assert decisions[1].reason == "no_averaging_down_block"