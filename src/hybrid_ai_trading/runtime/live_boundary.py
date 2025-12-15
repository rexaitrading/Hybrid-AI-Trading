from __future__ import annotations

import os

from hybrid_ai_trading.runtime.context_loader import load_run_context_from_env


def forbid_direct_ib_live(where: str) -> None:
    """
    Fail-closed guard for modules that call ib.placeOrder directly.

    Default: BLOCK in LIVE.
    Override only when: HAT_ALLOW_DIRECT_IB_LIVE=1 (not recommended).
    """
    ctx = load_run_context_from_env()
    if not ctx.is_live:
        return

    if (os.getenv("HAT_ALLOW_DIRECT_IB_LIVE", "") or "").strip() != "1":
        raise RuntimeError(
            f"[LIVE-BLOCKED] Direct IB live order path blocked in {where}. "
            f"Route via execution/brokers.py (canonical boundary) or set HAT_ALLOW_DIRECT_IB_LIVE=1."
        )

    # Even when explicitly allowed, enforce the full LIVE gate:
    ctx.require_live_safe()
