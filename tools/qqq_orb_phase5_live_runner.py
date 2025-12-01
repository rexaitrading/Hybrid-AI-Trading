"""
QQQ ORB Phase-5 live-style smoke runner (no IBG, no broker side-effects).

- Uses real ExecutionEngine (config-only) if ctor signature matches.
- Calls place_order_phase5_with_logging(...) once for QQQ.
- Exercises:
  - Phase-5 decisions gate (via phase5_gating_helpers),
  - No-averaging adapter,
  - Logging to logs/phase5_live_events.jsonl and qqq_phase5_paperlive_results.jsonl.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict

from hybrid_ai_trading.execution.execution_engine import (
    ExecutionEngine,
    place_order_phase5_with_logging,
)

# Central QQQ ORB Phase-5 config loader (JSON + EV band from YAML)
from tools.qqq_phase5_config_loader import (
    load_qqq_orb_phase5_config_with_ev,
)

# Robust import of Phase-5 gating helper:
# - When run as "python tools/qqq_orb_phase5_live_runner.py", top-level "" includes repo root.
# - When imported as "tools.qqq_orb_phase5_live_runner", PYTHONPATH includes "src".
try:
    from tools.phase5_gating_helpers import get_phase5_decision_for_trade
except Exception:  # pragma: no cover - fallback to old relative import
    from phase5_gating_helpers import get_phase5_decision_for_trade  # type: ignore[no-redef]


def build_example_config() -> Dict[str, Any]:
    """
    Example config enabling Phase-5 no-averaging for a live-style engine.

    NOTE: You may need to extend this with your real IB / data / cost config.
    """
    base: Dict[str, Any] = {
        "dry_run": True,  # SAFE: do not send real orders
        "phase5_no_averaging_down_enabled": True,
        "phase5": {
            "no_averaging_down_enabled": True,
        },
        # Extend as needed:
        # "costs": {...},
        # "broker": {...},
        # etc.
    }

    # Try to load QQQ ORB Phase-5 config (with EV band) for observability.
    # We do NOT currently merge it into the engine config to avoid changing
    # existing ctor expectations; we just print it so Block-E tuning can
    # confirm the EV band being used.
    try:
        qqq_cfg = load_qqq_orb_phase5_config_with_ev()
        ev_section = qqq_cfg.get("ev", {})
        print("[QQQ_ORB] Phase-5 EV config section:", ev_section)
    except Exception as e:
        print("[QQQ_ORB][WARN] Could not load QQQ ORB Phase-5 config with EV:", e)

    return base


def main() -> None:
    cfg = build_example_config()

    print("=== QQQ ORB Phase-5 live-style smoke ===")
    print("Config:", cfg)

    # Try to build a real ExecutionEngine with this config.
    try:
        engine = ExecutionEngine(config=cfg)
    except TypeError as e:
        print("\n[WARN] ExecutionEngine(config=...) ctor failed with TypeError:")
        print("      ", e)
        print("      Please adjust build_example_config() / ctor usage to match your engine.")
        return
    except Exception as e:
        print("\n[WARN] ExecutionEngine ctor failed:", e)
        return

    # Build a synthetic entry ts close to "now".
    entry_ts = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    # Dummy QQQ trade params for the smoke test.
    symbol = "QQQ"
    side = "BUY"
    qty = 1.0
    price = 1.0
    regime = "QQQ_ORB_LIVE"

    # Phase-5 decision via central helper (decisions JSON + ev_simple / EV bands).
    phase5_decision = get_phase5_decision_for_trade(
        entry_ts=entry_ts,
        symbol=symbol,
        regime=regime,
    )

    print("\nCalling place_order_phase5_with_logging(...)")
    print("  symbol =", symbol)
    print("  entry_ts =", entry_ts)
    print("  side =", side)
    print("  qty =", qty)
    print("  regime =", regime)
    print("  phase5_decision =", phase5_decision)

    result = place_order_phase5_with_logging(
        engine,
        symbol=symbol,
        entry_ts=entry_ts,
        side=side,
        qty=qty,
        price=price,
        regime=regime,
        phase5_decision=phase5_decision,
    )

    print("\nResult from place_order_phase5_with_logging:")
    print(result)

    print("\nIf logging is wired correctly, you should now see a new line in:")
    print("  logs/phase5_live_events.jsonl (if used)")
    print("and in logs/qqq_phase5_paperlive_results.jsonl via ExecutionEngine wrapper.")


if __name__ == "__main__":
    main()