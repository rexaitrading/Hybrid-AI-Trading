# === CLEAN + INDENTATION-SAFE + QOS-READY provider_quantcore.py ===

import time
import math
from typing import Dict, List, Any

from hybrid_ai_trading.runners.paper_utils import safe_float
from hybrid_ai_trading.providers.provider_qos import ProviderQoS


def _fake_md(symbol: str) -> float:
    """
    Safe mock price feed helper.
    Always returns finite floats. NEVER NaN.
    Replace with real provider hook in Phase-7.
    """
    return safe_float(100.0)


def provider_probe(universe: List[str], mdt: int = 3) -> Dict[str, Any]:
    """
    Phase-5 hardened upstream probe.
    MUST provide px, px_secondary, funds.usdcad, fx_secondary, order, session.
    MUST NEVER return NaN.
    """

    qos = ProviderQoS("provider_primary")

    t0 = time.time()

    # primary price
    px_primary = safe_float(_fake_md(universe[0])) if universe else None

    latency = (time.time() - t0) * 1000
    qos.record(latency_ms=latency, ok=True, price_ts=time.time())

    # secondary feed is always safe
    px_secondary = safe_float(px_primary)

    usdcad_primary = safe_float(1.35)
    fx_secondary = safe_float(1.3495)

    limit = safe_float(px_primary * 1.001, None)

    result = {
        "px": px_primary,
        "px_secondary": px_secondary,
        "funds": {
            "usdcad": usdcad_primary,
            "cad": 100000,
            "usd": 0.0,
        },
        "fx_secondary": fx_secondary,
        "order": {
            "action": "BUY",
            "qty": 1,
            "limit": limit,
        },
        "session": {
            "session": "EXT",
            "allow_ext": True,
            "ok_time": True,
        },
        "stale_ms": 0.0,  # Always fresh in mock
    }

    return result

def run_once(*args, **kwargs):
    """
    Placeholder entrypoint for QuantCore adapter.

    - Tests in tests/smoke/test_qc_adapter.py monkeypatch this function
      to simulate legacy/new-style QuantCore behaviors.
    - In production, implement this to call the real QuantCore engine.
    """
    raise RuntimeError(
        "paper_quantcore.run_once is a placeholder and should be "
        "monkeypatched in tests or implemented in live QuantCore wiring."
    )

# --- Safe default QuantCore run_once implementation ---
def run_once(symbols, price_map, risk_mgr):
    """
    Default QuantCore stub used in provider-only smoke tests.

    - symbols: iterable of symbols (e.g., ["AAPL"])
    - price_map: mapping symbol -> price (ignored here)
    - risk_mgr: risk manager object (ignored here)

    Returns a list of {"symbol": ..., "decision": {}} entries.
    Tests in tests/smoke/test_qc_adapter.py monkeypatch this function
    to simulate different behaviors; this is just a safe fallback.
    """
    out = []
    for s in list(symbols or []):
        out.append({"symbol": s, "decision": {}})
    return out
