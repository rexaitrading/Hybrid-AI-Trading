import math

from scripts.guardrails import load_guardrails, vet_and_adjust

from hybrid_ai_trading.runners.decision_schema import Decision
from hybrid_ai_trading.runners.sizing import kelly_capped_qty


def test_vet_and_adjust_spread_gate_blocks_when_bps_exceeds():
    g = load_guardrails()
    g["spread_bps_limit"] = 5.0
    ok, reason, d = vet_and_adjust("AAPL", {"price": 100.0, "bid": 99.0, "ask": 99.6, "qty": 10}, g)
    # spread = 0.6 -> 60 bps > 5 bps -> block
    assert ok is False
    assert "spread_" in reason
    assert d["qty"] == 0


def test_kelly_capped_qty_basic():
    qty = kelly_capped_qty(
        100000.0, price=250.0, f_raw=0.10, kelly_cap_by_regime={"neutral": 0.04}, regime="neutral"
    )
    # cap to 4% of 100k = 4,000 notional  floor(4000/250)=16
    assert qty == 16


def test_decision_to_item_shape():
    dec = Decision(
        symbol="MSFT",
        setup="ORB_Break",
        side="long",
        entry_px=100.0,
        stop_px=99.0,
        target_px=102.0,
        qty=10,
        kelly_f=0.05,
        regime="neutral",
        regime_conf=0.5,
        sentiment=0.0,
        sent_conf=0.5,
    )
    item = dec.to_item()
    assert item["symbol"] == "MSFT"
    assert "decision" in item
    assert item["decision"]["entry_px"] == 100.0
