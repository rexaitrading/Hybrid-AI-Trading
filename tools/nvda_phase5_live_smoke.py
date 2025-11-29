"""
NVDA Phase-5 live-style smoke runner (no IBG, no broker side-effects).

- Uses real ExecutionEngine (config-only) if ctor signature matches.
- Calls place_order_phase5_with_logging(...) once for NVDA.
- Exercises:
  - Phase-5 decisions gate (if decisions JSON + ts match),
  - No-averaging adapter,
  - Logging to logs/phase5_live_events.jsonl and optional paper_exec_logger.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict

from hybrid_ai_trading.execution.execution_engine import (
    ExecutionEngine,
    place_order_phase5_with_logging,
)


def build_example_config() -> Dict[str, Any]:
    """
    Example config enabling Phase-5 no-averaging for a live-style engine.

    NOTE: You may need to extend this with your real IB / data / cost config.
    """
    return {
        "dry_run": True,  # SAFE: do not send real orders
        "phase5_no_averaging_down_enabled": True,
        "phase5": {
            "no_averaging_down_enabled": True,
        },
        # You can extend with your existing fields, e.g.:
        # "costs": {...},
        # "broker": {...},
        # etc.
    }


def main() -> None:
    cfg = build_example_config()

    print("=== NVDA Phase-5 live-style smoke ===")
    print("Config:", cfg)

    # Try to build a real ExecutionEngine with this config.
    # If the ctor signature is different, we fail gracefully.
    try:
        engine = ExecutionEngine(config=cfg)  # adjust if your ctor differs
    except TypeError as e:
        print("\n[WARN] ExecutionEngine(config=...) ctor failed with TypeError:")
        print("      ", e)
        print("      Please adjust build_example_config() / ctor usage to match your engine.")
        return
    except Exception as e:
        print("\n[WARN] ExecutionEngine ctor failed:", e)
        return

    # Build a synthetic entry ts close to "now" for this smoke.
    # For a real live strategy, this should be the actual signal/bar timestamp.
    entry_ts = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    # Dummy NVDA trade params for the smoke test.
    # In your real strategy, these will be driven by your signal/kelly sizing.
    symbol = "NVDA"
    side = "BUY"
    qty = 1.0
    price = None
    regime = "NVDA_BPLUS_LIVE"

    print("\nCalling place_order_phase5_with_logging(...)")
    print("  symbol =", symbol)
    print("  entry_ts =", entry_ts)
    print("  side =", side)
    print("  qty =", qty)
    print("  regime =", regime)

    result = place_order_phase5_with_logging(
        engine,
        symbol=symbol,
        entry_ts=entry_ts,
        side=side,
        qty=qty,
        price=price,
        regime=regime,
    )

    print("\nResult from place_order_phase5_with_logging:")
    print(result)

    print("\nIf logging is wired correctly, you should now see a new line in:")
    print("  logs/phase5_live_events.jsonl")
    print("and, if paper_exec_logger.log_phase5_event/log_event exists,")
    print("  it should have been forwarded there as well.")


if __name__ == "__main__":
    main()
