import pytest

from hybrid_ai_trading.execution import execution_engine_phase5_guard as guard


class FakeDecision:
    """
    Minimal stand-in for Phase5RiskDecision for EV-band hard-veto tests.
    """

    def __init__(self, allowed: bool = True, reason: str | None = None) -> None:
        self.allowed = allowed
        self.reason = reason


@pytest.mark.parametrize("ev_value, expect_veto", [(-0.5, True), (0.5, False)])
def test_ev_band_hard_veto_flag_respects_ev_sign(monkeypatch, ev_value, expect_veto):
    """
    With PHASE5_ENABLE_EV_BAND_HARD_VETO=1:

    - ev < 0  -> guard should change decision.allowed to False and tag reason with 'ev_band_hard_veto'
    - ev > 0  -> guard should leave decision.allowed True and not tag the reason
    """

    # Enable hard veto for this test only
    monkeypatch.setenv("PHASE5_ENABLE_EV_BAND_HARD_VETO", "1")

    class FakeEngine:
        def __init__(self):
            # Expose a risk_manager so the guard path is used, not the fallback.
            self.risk_manager = fake_rm

    # Fake RiskManager + trade objects (guard_phase5_trade is monkeypatched)
    fake_rm = object()
    fake_trade = object()  # placeholder; guard builds its own trade dict anyway

    # Fake decision injected into guard_phase5_trade
    def fake_guard_phase5_trade(rm, trade):
        # We only care that the correct risk manager is passed; trade content is built by the guard.
        assert rm is fake_rm
        return FakeDecision(allowed=True, reason="base_reason")

    # Force EV hooks to see the EV we want to test
    def fake_extract_phase5_ev(decision):
        # ev_value, ev_band_abs, gate_score_v2
        return ev_value, 0.5, None

    monkeypatch.setattr(guard, "guard_phase5_trade", fake_guard_phase5_trade, raising=False)
    monkeypatch.setattr(guard, "_extract_phase5_ev", fake_extract_phase5_ev, raising=False)

    engine = FakeEngine()

    # Call the guarded wrapper. It should either block (ev < 0) or pass through (ev > 0).
    result = guard.place_order_phase5_with_guard(
        engine,
        trade=fake_trade,
        symbol="NVDA",
        side="BUY",
        qty=1.0,
        regime="NVDA_BPLUS_LIVE",
        mode="paper",
    )

    if expect_veto:
        # Hard veto: we expect the blocked_phase5 synthetic result
        assert result["status"] == "blocked_phase5"
        assert result.get("phase5_ev_band_enabled") is True
        assert result.get("phase5_ev_band_veto") is True
        reason = result.get("reason") or ""
        assert "ev_band_hard_veto" in reason
    else:
        # No veto: result should NOT be blocked, and no hard-veto tag.
        assert result.get("status") != "blocked_phase5"
        # Advisory fields should still be present and show no veto.
        assert result.get("phase5_ev_band_enabled") in (True, False)
        assert result.get("phase5_ev_band_veto") is False
        reason = result.get("reason") or ""
        assert "ev_band_hard_veto" not in reason