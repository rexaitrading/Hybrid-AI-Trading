"""
Tests for Phase5RiskAdapter stub.

Goal:
- Verify the stub adapter always allows trades.
- Verify the stub reason string is explicit so JSONL / Notion
  can never confuse this with real risk wiring.
"""

from hybrid_ai_trading.risk.risk_phase5_paper_adapter import Phase5RiskAdapter


def test_phase5_risk_adapter_stub_allows_basic_trade():
    adapter = Phase5RiskAdapter()

    trade = {
        "symbol": "SPY",
        "side": "BUY",
        "qty": 1,
        "price": 500.0,
        "regime": "SPY_ORB_REPLAY",
        "ts": "2025-11-10T14:45:00+00:00",
    }

    result = adapter.check_trade(trade)

    assert result["allowed"] is True
    assert "phase5_risk_adapter_stub" in result["reason"]


def test_phase5_risk_adapter_stub_handles_missing_fields():
    adapter = Phase5RiskAdapter()

    # Minimal dict – rely on defaults in _build_context.
    trade = {"symbol": "QQQ"}

    result = adapter.check_trade(trade)

    assert result["allowed"] is True
    assert "phase5_risk_adapter_stub" in result["reason"]