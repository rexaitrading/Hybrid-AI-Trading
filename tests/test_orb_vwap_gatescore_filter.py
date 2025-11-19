from pathlib import Path
import json

from tools.orb_vwap_gatescore_filter import filter_trades


def test_filter_trades_respects_edge_ratio_and_cost_and_pnl(tmp_path: Path) -> None:
    # Synthetic config: simple thresholds
    cfg = {
        "gatescore_edge_ratio_min": 0.04,
        "max_cost_bp": 3.0,
        "min_pnl_pct_training": -0.01,
    }

    # Three synthetic trades:
    #  1) Good edge, acceptable cost, positive pnl -> should PASS
    #  2) Edge too low -> should FAIL
    #  3) Cost too high -> should FAIL
    trades = [
        {
            "symbol": "AAPL",
            "gatescore_edge_ratio": 0.047,
            "cost_bp": 2.5,
            "pnl_pct": 0.001,
        },
        {
            "symbol": "AAPL",
            "gatescore_edge_ratio": 0.030,
            "cost_bp": 2.0,
            "pnl_pct": 0.002,
        },
        {
            "symbol": "AAPL",
            "gatescore_edge_ratio": 0.050,
            "cost_bp": 4.0,
            "pnl_pct": 0.003,
        },
    ]

    gated = filter_trades(trades, cfg)

    # Only the first trade should pass
    assert len(gated) == 1
    assert gated[0]["symbol"] == "AAPL"
    assert gated[0]["gatescore_edge_ratio"] == 0.047
    assert gated[0]["cost_bp"] == 2.5


def test_filter_trades_allows_negative_pnl_when_threshold_low(tmp_path: Path) -> None:
    # Allow slightly negative pnl for training data
    cfg = {
        "gatescore_edge_ratio_min": 0.04,
        "max_cost_bp": 3.0,
        "min_pnl_pct_training": -0.005,
    }

    trades = [
        {
            "symbol": "AAPL",
            "gatescore_edge_ratio": 0.050,
            "cost_bp": 2.0,
            "pnl_pct": -0.004,  # small loser, but above -0.005 threshold
        },
        {
            "symbol": "AAPL",
            "gatescore_edge_ratio": 0.050,
            "cost_bp": 2.0,
            "pnl_pct": -0.010,  # too negative, should fail
        },
    ]

    gated = filter_trades(trades, cfg)

    # Only the first trade should pass the training filter
    assert len(gated) == 1
    assert gated[0]["pnl_pct"] == -0.004