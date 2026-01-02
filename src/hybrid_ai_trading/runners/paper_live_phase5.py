# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import inspect
import os
import sys
import time
from typing import Any, Optional


def _try_import_run_once() -> Optional[Any]:
    """
    Best-effort import of an existing paper execution primitive.
    We do NOT assume exact module names (repo evolves). We try common ones.
    """
    candidates = [
        # common "paper runner" modules in this repo
        ("hybrid_ai_trading.runners.paper_quantcore", "run_once"),
        ("hybrid_ai_trading.runners.paper_runner", "run_once"),
        ("hybrid_ai_trading.runners.paper_live", "run_once"),
        # fallback: any central execution function
        ("hybrid_ai_trading.execution.engine", "run_once"),
    ]
    for mod, fn in candidates:
        try:
            m = __import__(mod, fromlist=[fn])
            if hasattr(m, fn):
                return getattr(m, fn)
        except Exception:
            continue
    return None


def main() -> int:
    ap = argparse.ArgumentParser("Paper Live Phase-5 (safe stub)")
    ap.add_argument("--symbol", default="NVDA")
    ap.add_argument("--iterations", type=int, default=200)
    ap.add_argument("--sleep-ms", type=int, default=500)
    ap.add_argument("--config", default="")
    args = ap.parse_args()

    # Hard enforce paper mode
    os.environ["HAT_IS_PAPER"] = "1"

    run_once = _try_import_run_once()
    if run_once is None:
        print("[PAPER-LIVE] ERROR: Could not locate a run_once() function. "
              "Wire this runner to your actual execution loop.")
        return 2

    print(f"[PAPER-LIVE] Starting paper loop symbol={args.symbol} iters={args.iterations} sleep_ms={args.sleep_ms}")
    for i in range(args.iterations):
        try:
            sig = inspect.signature(run_once)
            params = list(sig.parameters.keys())

            # Common variants:
            # 1) run_once(symbol="NVDA")
            if "symbol" in params:
                run_once(symbol=args.symbol)
            # 2) run_once(symbols=[...], price_map={...}, risk_mgr=...)
            elif "symbols" in params and "price_map" in params and "risk_mgr" in params:
                symbols = [args.symbol]
                # price_map is required; for paper/live, downstream should replace with real quotes
                price_map = {args.symbol: 0.0}
                # risk_mgr required: try to construct from repo if available
                try:
                    from hybrid_ai_trading.risk.risk_manager import RiskManager  # type: ignore
                    risk_mgr = RiskManager()
                except Exception:
                    risk_mgr = object()  # fail-closed later if real risk mgr is required
                run_once(symbols, price_map, risk_mgr)
            else:
                # Last resort: call with no args (legacy)
                run_once()

        except Exception as e:
            print(f"[PAPER-LIVE] Iteration {i} error: {e!r}")
            return 3

        time.sleep(max(0.0, args.sleep_ms / 1000.0))

    print("[PAPER-LIVE] Completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())