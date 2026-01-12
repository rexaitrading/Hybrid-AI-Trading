from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict

from hybrid_ai_trading.brokers.ib_client import IBClient, IBConfig
from hybrid_ai_trading.execution.execution_engine import ExecutionEngine
from hybrid_ai_trading.execution.order_manager import OrderManager


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", default=os.environ.get("HAT_MARKET", "US"))
    ap.add_argument("--symbol", default="ALL")
    args = ap.parse_args(argv)

    # Best-effort: connect only when needed; IBClient.session handles connect/disconnect.
    cfg = IBConfig()
    live = IBClient(cfg)

    # OrderManager expects live_client for live path
    om = OrderManager(live_client=live, use_paper_simulator=False, simulator=None)

    eng = ExecutionEngine(order_manager=om, paper_simulator=None, dry_run=False)

    # Use a session to ensure IB disconnect even on errors
    try:
        with live.session():
            out: Dict[str, Any] = eng.emergency_flatten()
            # Print a compact summary; do not leak secrets
            sys.stdout.write(str(out) + "\n")
            return 0
    except Exception as e:
        sys.stderr.write(f"[CRASHMODE_FLATTEN] FAIL: {e!r}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
