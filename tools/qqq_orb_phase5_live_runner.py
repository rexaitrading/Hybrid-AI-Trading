"""
QQQ ORB Phase-5 live-style smoke runner (no IBG, no broker side-effects).

- Uses real ExecutionEngine (config-only) if ctor signature matches.
- Calls place_order_phase5_with_logging(...) once for QQQ.
- Exercises:
  - Phase-5 decisions gate (via phase5_gating_helpers),
  - No-averaging adapter,
  - Logging to logs/phase5_live_events.jsonl and qqq_phase5_paperlive_results.jsonl,
  - Soft EV diagnostics and EV-band hard veto suggestion (log-only),
  - ORB+VWAP EV model (ev_orb_vwap_model, log-only).
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

from tools.qqq_phase5_config_loader import (
    load_qqq_orb_phase5_config_with_ev,
)

try:
    from tools.phase5_gating_helpers import get_phase5_decision_for_trade, attach_ev_band_hard_veto
except Exception:  # pragma: no cover
    from phase5_gating_helpers import get_phase5_decision_for_trade, attach_ev_band_hard_veto  # type: ignore[no-redef]

from hybrid_ai_trading.risk.ev_orb_vwap_model import (
    OrbVwapFeatures,
    compute_orb_vwap_ev,
    compute_effective_ev,
)

QQQ_EV_PER_TRADE = 0.0075  # from config/phase5/ev_simple.json (ev_per_trade for QQQ_ORB_LIVE)

QQQ_PAPER_JSONL_PATH = Path("logs") / "qqq_phase5_paperlive_results.jsonl"


def compute_soft_veto_ev_fields(ev: float, realized_pnl: float) -> Dict[str, Any]:
    abs_ev = abs(ev)

    # QQQ-specific bands based on EV per trade ~0.0075:
    #   Band 0: |EV| <= 0.0038  (~0.5 * EV)
    #   Band 1: 0.0038 < |EV| <= 0.0113  (~1.5 * EV)
    #   Band 2: |EV| > 0.0113
    if abs_ev <= 0.0038:
        ev_band_abs = 0
    elif abs_ev <= 0.0113:
        ev_band_abs = 1
    else:
        ev_band_abs = 2

    ev_gap_abs = abs(ev - realized_pnl)
    ev_vs_realized_paper = ev - realized_pnl
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


def append_qqq_phase5_paper_entry(
    ts: str,
    symbol: str,
    regime: str,
    side: str,
    price: float,
    result: Dict[str, Any],
    phase5_decision: Dict[str, Any],
) -> None:
    """
    Append a QQQ Phase-5 soft EV diagnostic entry to qqq_phase5_paperlive_results.jsonl,
    enriched with soft EV diagnostics, EV-band hard veto suggestion, and ORB+VWAP EV model.
    """
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

    decision_for_hard: Dict[str, Any] = {
        "ev": ev,
        "phase5_allowed": phase5_allowed,
        "phase5_reason": phase5_reason,
        "realized_pnl_paper": realized_pnl,
        "ev_gap_abs": soft_fields.get("ev_gap_abs"),
    }
    decision_for_hard = attach_ev_band_hard_veto(
        decision=decision_for_hard,
        realized_pnl=realized_pnl,
        gap_threshold=0.7,
    )

    orb_strength = 0.5 if side.upper() == "BUY" else 0.3
    above_vwap = True if side.upper() == "BUY" else False
    trend_score = 0.0
    vol_bucket = "medium"

    features = OrbVwapFeatures(
        orb_strength=orb_strength,
        above_vwap=above_vwap,
        trend_score=trend_score,
        vol_bucket=vol_bucket,
    )
    ev_orb_vwap_model = compute_orb_vwap_ev(
        symbol=symbol,
        regime=regime,
        features=features,
    )

    ev_effective_orb_vwap = compute_effective_ev(
        ev_phase5=ev,
        ev_model=ev_orb_vwap_model,
    )\

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

    entry["ev_hard_veto"] = decision_for_hard.get("ev_hard_veto")
    entry["ev_hard_veto_reason"] = decision_for_hard.get("ev_hard_veto_reason")
    entry["ev_hard_veto_gap_abs"] = decision_for_hard.get("ev_hard_veto_gap_abs")
    entry["ev_hard_veto_gap_threshold"] = decision_for_hard.get("ev_hard_veto_gap_threshold")

    entry["ev_orb_vwap_model"] = ev_orb_vwap_model
    entry["ev_effective_orb_vwap"] = ev_effective_orb_vwap

    QQQ_PAPER_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with QQQ_PAPER_JSONL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def build_example_config() -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "dry_run": True,
        "phase5_no_averaging_down_enabled": True,
        "phase5": {
            "no_averaging_down_enabled": True,
        },
    }
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

    try:
        engine = ExecutionEngine(config=cfg)
    except TypeError as e:
        print("\n[WARN] ExecutionEngine(config=...) ctor failed with TypeError:")
        print("      ", e)
        return
    except Exception as e:
        print("\n[WARN] ExecutionEngine ctor failed:", e)
        return

    entry_ts = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    symbol = "QQQ"
    side = "BUY"
    qty = 1.0
    price = 1.0
    regime = "QQQ_ORB_LIVE"

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

    try:
        append_qqq_phase5_paper_entry(
            ts=entry_ts,
            symbol=symbol,
            regime=regime,
            side=side,
            price=price,
            result=result,
            phase5_decision=phase5_decision,
        )
        print("\n[PHASE5/QQQ] Appended soft+hard EV + ORB+VWAP EV diagnostic entry to", QQQ_PAPER_JSONL_PATH)
    except Exception as e:
        print("\n[WARN] Failed to append QQQ soft/hard EV diagnostic entry:", e)

    print("\nIf logging is wired correctly, you should now see a new line in:")
    print("  logs/phase5_live_events.jsonl (if used)")
    print("and in logs/qqq_phase5_paperlive_results.jsonl via ExecutionEngine wrapper")
    print("plus the soft + hard EV + ORB+VWAP EV diagnostic entry appended by this runner.")


if __name__ == "__main__":
    main()