from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict

from hybrid_ai_trading.brokers.ib_client import IBClient, IBConfig
from hybrid_ai_trading.execution.order_manager import OrderManager


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", default=os.environ.get("HAT_MARKET", "US"))
    ap.add_argument("--symbol", default="ALL")
    args = ap.parse_args(argv)

    # Connect only inside session; always disconnect.
    cfg = IBConfig()
    live = IBClient(cfg)

    # Live OrderManager path (we wired flatten_all() to IBClient cancel/close primitives)
    om = OrderManager(live_client=live, use_paper_simulator=False, simulator=None)

    try:
        with live.session():
            out: Dict[str, Any] = om.flatten_all()
            sys.stdout.write(str(out) + "\n")
            return 0
    except Exception as e:
        sys.stderr.write(f"[CRASHMODE_FLATTEN] FAIL: {e!r}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
