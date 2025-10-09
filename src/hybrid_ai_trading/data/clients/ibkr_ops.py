from __future__ import annotations
"""
IBKR Ops (Hybrid AI Quant Pro v1.0 - Practical Ops Tools)
- --account
- --positions
- --open-orders
- --cancel-all [--symbol]
Notes:
- Defaults to TWS Paper (127.0.0.1:7497, clientId=1, readonly=True).
- Override with IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID if needed.
"""

import argparse
import json
import os
from ib_insync import IB
from hybrid_ai_trading.data.clients.ibkr_client import connect_ib, account_summary, positions, open_orders, cancel_all


def _print(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=True))


def main() -> None:
    ap = argparse.ArgumentParser(description="IBKR ops helper")
    ap.add_argument("--account", action="store_true")
    ap.add_argument("--positions", action="store_true")
    ap.add_argument("--open-orders", action="store_true")
    ap.add_argument("--cancel-all", action="store_true")
    ap.add_argument("--symbol", type=str)
    args = ap.parse_args()

    ib: IB = connect_ib()

    try:
        if args.account:
            _print(account_summary(ib)); return
        if args.positions:
            _print(positions(ib)); return
        if args.open_orders:
            _print(open_orders(ib)); return
        if args.cancel_all:
            _print(cancel_all(ib, args.symbol)); return
        # default
        _print(account_summary(ib))
    finally:
        ib.disconnect()


if __name__ == "__main__":
    main()
