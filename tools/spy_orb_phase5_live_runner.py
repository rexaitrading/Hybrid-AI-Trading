"""
SPY ORB Phase-5 live-style smoke runner (no IBG, no broker side-effects).

- Uses real ExecutionEngine (config-only) if ctor signature matches.
- Calls place_order_phase5_with_logging(...) once for SPY.
- Exercises:
  - Phase-5 decisions gate (via phase5_gating_helpers),
  - No-averaging adapter,
  - Logging to logs/phase5_live_events.jsonl and spy_phase5_paperlive_results.jsonl.
"""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict

from hybrid_ai_trading.execution.execution_engine import (
    ExecutionEngine,
    place_order_phase5_with_logging,
)

# Central SPY ORB Phase-5 config loader (JSON + EV band from YAML)
from spy_phase5_config_loader import (
    load_spy_orb_phase5_config_with_ev,
)

# Robust import of Phase-5 gating helper:
# - When run as "python tools/spy_orb_phase5_live_runner.py", top-level "" includes repo root.
# - When imported as "tools.spy_orb_phase5_live_runner", PYTHONPATH includes "src".
try:
    from tools.phase5_gating_helpers import get_phase5_decision_for_trade
except Exception:  # pragma: no cover - fallback to old relative import
    from phase5_gating_helpers import get_phase5_decision_for_trade  # type: ignore[no-redef]


SPY_PAPER_JSONL_PATH = Path("logs") / "spy_phase5_paperlive_results.jsonl"


def compute_soft_veto_ev_fields(ev: float, realized_pnl: float) -> Dict[str, Any]:
    """
    Phase-5 SPY soft EV veto diagnostics.

    This is *diagnostic only*:
    - soft_ev_veto: whether EV-vs-realized gap is large
    - soft_ev_reason: short text reason
    - ev_band_abs: 0/1/2 coarse band for |EV|
    - ev_gap_abs: |EV - realized_pnl|
    - ev_vs_realized_paper: EV - realized_pnl
    - ev_band_veto_applied: False for now (soft only)
    """
    abs_ev = abs(ev)
    if abs_ev <= 0.15:
        ev_band_abs = 0
    elif abs_ev <= 0.30:
        ev_band_abs = 1
    else:
        ev_band_abs = 2

    ev_gap_abs = abs(ev - realized_pnl)
    ev_vs_realized_paper = ev - realized_pnl

    # Soft veto rule: gap >= 0.20R triggers a "hit"
    ev_hit_flag = ev_gap_abs >= 0.20

    return {
        "soft_ev_veto": ev_hit_flag,
        "soft_ev_reason": "ev_gap>=0.20" if ev_hit_flag else None,
        "ev_band_abs": ev_band_abs,
        "ev_gap_abs": ev_gap_abs,
        "ev_hit_flag": ev_hit_flag,
        "ev_vs_realized_paper": ev_vs_realized_paper,
        "ev_band_veto_applied": False,
        "ev_band_veto_reason": None,
    }


def append_spy_phase5_paper_entry(
    ts: str,
    symbol: str,
    regime: str,
    side: str,
    price: float,
    result: Dict[str, Any],
    phase5_decision: Dict[str, Any],
) -> None:
    """
    Append a SPY Phase-5 soft EV diagnostic entry to spy_phase5_paperlive_results.jsonl.

    This is SPY-specific and *does not* change any trade gating behavior.
    """
    # Realized PnL not yet wired in ExecutionEngine result -> assume 0.0 for smoke.
    try:
        realized_pnl = float(result.get("realized_pnl_paper", 0.0))
    except (TypeError, ValueError):
        realized_pnl = 0.0

    try:
        ev = float(phase5_decision.get("ev", 0.0))
    except (TypeError, ValueError):
        ev = 0.0

    phase5_allowed = bool(phase5_decision.get("allowed", True))
    phase5_reason = phase5_decision.get("reason", "unknown")

    soft_fields = compute_soft_veto_ev_fields(ev=ev, realized_pnl=realized_pnl)

    entry: Dict[str, Any] = {
        "ts": ts,
        "symbol": symbol,
        "regime": regime,
        "side": side,
        "price": price,
        "realized_pnl_paper": realized_pnl,
        "ev": ev,
        "phase5_allowed": phase5_allowed,
        "phase5_reason": phase5_reason,
    }
    entry.update(soft_fields)

    SPY_PAPER_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SPY_PAPER_JSONL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


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

    # Try to load SPY ORB Phase-5 config (with EV band) for observability.
    # We do NOT currently merge it into the engine config to avoid changing
    # existing ctor expectations; we just print it so Block-E tuning can
    # confirm the EV band being used.
    try:
        spy_cfg = load_spy_orb_phase5_config_with_ev()
        ev_section = spy_cfg.get("ev", {})
        print("[SPY_ORB] Phase-5 EV config section:", ev_section)
    except Exception as e:
        print("[SPY_ORB][WARN] Could not load SPY ORB Phase-5 config with EV:", e)

    return base


def main() -> None:
    cfg = build_example_config()

    print("=== SPY ORB Phase-5 live-style smoke ===")
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

    # Dummy SPY trade params for the smoke test.
    symbol = "SPY"
    side = "BUY"
    qty = 1.0
    price = 1.0
    regime = "SPY_ORB_LIVE"

    # Phase-5 decision via central helper (decisions JSON + ev_simple / EV bands).
    phase5_decision = get_phase5_decision_for_trade(
        entry_ts=entry_ts,
        symbol=symbol,
        regime=regime,
    )
    if not phase5_decision:
        phase5_decision = {
            "ev": 0.0,
            "allowed": True,
            "reason": "ev_simple_default",
        }

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

    # Append SPY-specific soft EV diagnostics (diagnostic only).
    try:
        append_spy_phase5_paper_entry(
            ts=entry_ts,
            symbol=symbol,
            regime=regime,
            side=side,
            price=price,
            result=result,
            phase5_decision=phase5_decision,
        )
        print("\n[PHASE5/SPY] Appended soft EV diagnostic entry to", SPY_PAPER_JSONL_PATH)
    except Exception as e:
        print("\n[WARN] Failed to append SPY soft EV diagnostic entry:", e)

    print("\nIf logging is wired correctly, you should now see a new line in:")
    print("  logs/phase5_live_events.jsonl (if used)")
    print("and in logs/spy_phase5_paperlive_results.jsonl via ExecutionEngine wrapper")
    print("plus the soft EV diagnostic entry appended by this runner.")


if __name__ == "__main__":
    main()