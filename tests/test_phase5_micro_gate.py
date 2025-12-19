from hybrid_ai_trading.risk.risk_phase5_micro_gate import micro_gate_for_symbol


def test_micro_gate_green_regime_allows():
    # Very tight spreads and tiny range -> GREEN, allowed
    dec = micro_gate_for_symbol("SPY", ms_range_pct=0.001, est_spread_bps=0.5, est_fee_bps=0.1)
    assert dec.allowed is True
    assert dec.regime == "GREEN"
    assert "GREEN" in dec.reason


def test_micro_gate_red_regime_blocks_spy():
    # Big range and big costs -> RED, blocked for SPY
    dec = micro_gate_for_symbol("SPY", ms_range_pct=0.02, est_spread_bps=3.0, est_fee_bps=0.5)
    assert dec.allowed is False
    assert dec.regime == "RED"
    assert "RED" in dec.reason


def test_micro_gate_red_regime_blocks_qqq():
    dec = micro_gate_for_symbol("QQQ", ms_range_pct=0.02, est_spread_bps=3.0, est_fee_bps=0.5)
    assert dec.allowed is False
    assert dec.regime == "RED"


def test_micro_gate_non_spy_qqq_not_gated():
    # Non-SPY/QQQ should not be hard-blocked by this helper
    dec = micro_gate_for_symbol("NVDA", ms_range_pct=0.02, est_spread_bps=3.0, est_fee_bps=0.5)
    assert dec.allowed is True
    assert "symbol not gated" in dec.reason
