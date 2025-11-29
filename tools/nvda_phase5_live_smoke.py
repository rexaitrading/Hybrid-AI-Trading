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
from pathlib import Path
import json

from hybrid_ai_trading.execution.execution_engine import (
    ExecutionEngine,
    place_order_phase5_with_logging,
)


def _load_nvda_phase5_decision(entry_ts: str) -> Dict[str, Any]:
    """
    Load a Phase-5 decision for NVDA matching entry_ts from decisions JSONL.

    Best-effort helper for smoke / live-style tests:
    - Reads logs/nvda_phase5_decisions.jsonl (adjust path if needed).
    - Looks for a record whose 'entry_ts' or 'ts' equals entry_ts.
    - Returns ev / ev_band_abs / allowed / reason.
    - Falls back to a default dict if anything goes wrong.
    """
    decisions_path = Path("logs") / "nvda_phase5_decisions.jsonl"
    default_decision: Dict[str, Any] = {
        "ev": 0.0,
        "ev_band": None,
        "ev_band_abs": 0.0,
        "allowed": True,
        "reason": "risk_ok",
    }

    try:
        if not decisions_path.exists():
            return default_decision

        matched: Dict[str, Any] | None = None

        with decisions_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue

                ts_val = obj.get("entry_ts") or obj.get("ts")
                if ts_val == entry_ts:
                    matched = obj
                    break

        if matched is None:
            return default_decision

        # Extract EV fields (handle nested or flat structures)
        ev_val = matched.get("ev")
        if isinstance(ev_val, dict):
            ev = ev_val.get("mu", 0.0)
            ev_band_abs = ev_val.get("band_abs") or ev_val.get("band") or 0.0
        else:
            ev = ev_val if ev_val is not None else 0.0
            ev_band_abs = matched.get("ev_band_abs") or matched.get("ev_band") or 0.0

        allowed = bool(matched.get("allowed", True))
        reason = matched.get("reason", "risk_ok")

        return {
            "ev": float(ev),
            "ev_band": None,
            "ev_band_abs": float(ev_band_abs),
            "allowed": allowed,
            "reason": reason,
        }
    except Exception:
        return default_decision


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
    price = 1.0  # safe dummy price for smoke (avoid portfolio_update_failed)
    regime = "NVDA_BPLUS_LIVE"

    # Load real Phase-5 decision (best-effort) for this entry_ts
    phase5_decision = _load_nvda_phase5_decision(entry_ts)

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
    print("and in logs/nvda_phase5_paperlive_results.jsonl via ExecutionEngine wrapper.")


if __name__ == "__main__":
    main()