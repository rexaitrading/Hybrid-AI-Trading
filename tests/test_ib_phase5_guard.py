from types import SimpleNamespace

from hybrid_ai_trading.ib.ib_phase5_guard import place_order_with_phase5_guard
from hybrid_ai_trading.risk.risk_phase5_types import Phase5RiskDecision


def test_place_order_with_phase5_guard_allows_stub_ok():
    # RiskManager-like stub
    rm = SimpleNamespace(
        check_trade_phase5=lambda trade: Phase5RiskDecision(
            allowed=True,
            reason="phase5_risk_ok",
            details={},
        )
    )

    # Dummy ib_client / contract / order
    ib_client = object()
    contract = object()
    order = object()

    trade_context = {
        "symbol": "SPY",
        "side": "BUY",
        "qty": 1.0,
        "price": 500.0,
        "regime": "SPY_ORB_LIVE",
        "day_id": "2025-11-10",
    }

    result = place_order_with_phase5_guard(
        rm=rm,
        ib_client=ib_client,
        contract=contract,
        order=order,
        trade_context=trade_context,
    )

    assert result["status"] == "ok_stub_ib"