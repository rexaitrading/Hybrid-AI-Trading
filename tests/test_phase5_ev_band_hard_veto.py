from hybrid_ai_trading.risk.phase5_ev_band_hard_veto import (
    evaluate_ev_band_hard_veto,
)


def test_ev_negative_triggers_hard_veto():
    result = evaluate_ev_band_hard_veto(ev=-0.10, realized_pnl=0.0, gap_threshold=0.7)
    assert result.hard_veto is True
    assert result.hard_veto_reason == "ev<0"
    assert result.ev_gap_abs == 0.10


def test_large_gap_triggers_hard_veto():
    # EV positive, but realized PnL far away: gap >= threshold
    result = evaluate_ev_band_hard_veto(ev=0.20, realized_pnl=-0.80, gap_threshold=0.7)
    assert result.hard_veto is True
    assert result.hard_veto_reason == "ev_gap>=threshold"
    # abs(0.20 - -0.80) = 1.0
    assert result.ev_gap_abs == 1.0


def test_normal_case_does_not_trigger_hard_veto():
    # EV small positive, PnL close, gap < threshold
    result = evaluate_ev_band_hard_veto(ev=0.10, realized_pnl=0.05, gap_threshold=0.7)
    assert result.hard_veto is False
    assert result.hard_veto_reason is None
    assert result.ev_gap_abs == 0.05