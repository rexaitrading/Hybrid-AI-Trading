# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
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
            # We pass only the safest common arg: symbol.
            # If your run_once signature differs, update this file accordingly.
            run_once(symbol=args.symbol)
        except TypeError:
            # If signature is different, call without kwargs.
            run_once()
        except Exception as e:
            print(f"[PAPER-LIVE] Iteration {i} error: {e!r}")
            return 3

        time.sleep(max(0.0, args.sleep_ms / 1000.0))

    print("[PAPER-LIVE] Completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())