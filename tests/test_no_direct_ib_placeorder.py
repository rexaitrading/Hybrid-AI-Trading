from __future__ import annotations

from pathlib import Path

# Baseline regression guard:
# These are the ONLY files currently allowed to contain direct `ib.placeOrder(`.
# If new call sites appear, this test FAILS (fail-closed).
ALLOWED_FILES = {
    "src/hybrid_ai_trading/broker/ib_safe.py",
    "src/hybrid_ai_trading/brokers/ib_adapter.py",
    "src/hybrid_ai_trading/execution/brokers.py",
    "src/hybrid_ai_trading/execution/paper_order.py",
    "src/hybrid_ai_trading/data/clients/ibkr_client.py",
    "src/hybrid_ai_trading/pipelines/daily_stock_dashboard.py",
    "src/hybrid_ai_trading/runners/ah_once.py",
    "src/hybrid_ai_trading/runners/runner_stream.py",
    "src/hybrid_ai_trading/utils/preflight.py",
    "src/hybrid_ai_trading/utils/risk.py",
}

def test_no_new_direct_ib_placeorder_call_sites():
    root = Path("src/hybrid_ai_trading")
    offenders: list[str] = []

    for p in root.rglob("*.py"):
        txt = p.read_text(encoding="utf-8-sig")
        if "ib.placeOrder(" not in txt:
            continue

        rel = str(p).replace("\\", "/")
        if rel not in ALLOWED_FILES:
            offenders.append(rel)

    assert not offenders, (
        "New direct ib.placeOrder call sites detected (must route via IB chokepoint): "
        + ", ".join(sorted(offenders))
    )
