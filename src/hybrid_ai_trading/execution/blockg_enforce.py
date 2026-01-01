import json
from hybrid_ai_trading.execution.blockg_errors import BlockGNotReady
import os
from typing import Any, Dict, Optional
def load_blockg_status() -> Dict[str, Any]:
    """
    Load Block-G status JSON from env HAT_BLOCKG_STATUS_PATH (fail-closed).
    """
    path = (os.environ.get("HAT_BLOCKG_STATUS_PATH", "") or "").strip()
    if not path:
        raise BlockGNotReady("BLOCK-G DENY: missing HAT_BLOCKG_STATUS_PATH")

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise BlockGNotReady(f"BLOCK-G DENY: failed to read status: {e!r}")


# backward compatibility (some callers/tests use this name)
def _load_blockg_status() -> Dict[str, Any]:
    return load_blockg_status()


def require_blockg_ready_for_live(symbol: str, *, status: Optional[Dict[str, Any]] = None) -> None:
    """
    LIVE gate used by execution/broker chokepoints.

    Contract:
      - If symbol unknown => fail-closed
      - If per-symbol readiness false => raise BlockGNotReady containing '<key>=false'
      - If status is provided => use it (test-friendly); else load from env path
    """
    sym = (symbol or "").strip().upper()
    key_map = {
        "NVDA": "nvda_blockg_ready",
        "SPY":  "spy_blockg_ready",
        "QQQ":  "qqq_blockg_ready",
    }
    k = key_map.get(sym)
    if not k:
        raise BlockGNotReady(f"BLOCK-G DENY (live): unknown symbol={sym}")

    st = status if isinstance(status, dict) else _load_blockg_status()

    ok = bool(st.get(k, False))
    if not ok:
        reasons = st.get("reasons_not_ready", [])
        # Keep message stable for tests: must contain '<key>=false'
        raise BlockGNotReady(f"{k}=false reasons={reasons}")
