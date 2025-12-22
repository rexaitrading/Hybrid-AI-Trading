from __future__ import annotations

from pathlib import Path

ALLOWED_SUBSTRINGS = (
    "src/hybrid_ai_trading/brokers/ib_adapter.py",
    "src/hybrid_ai_trading/broker/ib_safe.py",
    "src/hybrid_ai_trading/execution/brokers.py",
    "src/hybrid_ai_trading/execution/paper_order.py",
)def test_no_direct_ib_placeorder_outside_allowed():
    root = Path("src/hybrid_ai_trading")
    hits: list[str] = []
    for p in root.rglob("*.py"):
        txt = p.read_text(encoding="utf-8-sig")
        if "ib.placeOrder(" in txt:
            rel = str(p).replace("\\", "/")
            if not any(a in rel for a in ALLOWED_SUBSTRINGS):
                hits.append(rel)
    assert not hits, "Direct ib.placeOrder found outside allowed files: " + ", ".join(hits)
