from __future__ import annotations

"""
NVDA Phase-5 live-style runner for IB paper trading.

- Uses real ExecutionEngine with a minimal config.
- Calls place_order_phase5_with_logging(...) once for NVDA.
- Exercises:
  * Phase-5 decisions gate (should_allow_trade)
  * RiskManager.phase5_no_averaging_down_for_symbol adapter
  * Logging to logs/phase5_live_events.jsonl and optional paper_exec_logger.
  * Soft EV diagnostics and EV-band hard veto suggestion (log-only).
  * ORB+VWAP model EV (ev_orb_vwap_model, log-only).
"""

import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from hybrid_ai_trading.execution.execution_engine import (
    ExecutionEngine,
    place_order_phase5_with_logging,
)
from hybrid_ai_trading.risk.risk_phase5_account_caps import account_daily_loss_gate
from hybrid_ai_trading.risk.phase5_ev_band_hard_veto import evaluate_ev_band_hard_veto
from hybrid_ai_trading.risk.ev_orb_vwap_model import (
    OrbVwapFeatures,
    compute_orb_vwap_ev,
    compute_effective_ev,
)

IPO_WATCHLIST_PATH = Path("logs") / "ipo_watchlist.jsonl"
NVDA_PAPER_JSONL_PATH = Path("logs") / "nvda_phase5_paperlive_results.jsonl"

# NVDA Phase-5 EV bands + thresholds (tuned via replay/paper)
NVDA_EV_BAND0_MAX = 0.0062
NVDA_EV_BAND1_MAX = 0.0184
NVDA_SOFT_VETO_GAP_THRESHOLD = 0.20
NVDA_HARD_VETO_GAP_THRESHOLD = 0.7


def load_ipo_tags() -> Dict[str, Dict[str, Any]]:
    tags: Dict[str, Dict[str, Any]] = {}
    if not IPO_WATCHLIST_PATH.exists():
        return tags

    with IPO_WATCHLIST_PATH.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            symbol = str(entry.get("symbol", "")).upper()
            if not symbol:
                continue
            tags[symbol] = entry
    return tags


def get_account_daily_loss_cap_from_env(default: float = 50.0) -> float:
    value = os.environ.get("HAT_PHASE5_ACCOUNT_DAILY_LOSS_CAP")
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def get_phase5_decision_for_trade(
    entry_ts: str,
    symbol: str,
    regime: str,
) -> Optional[Dict[str, Any]]:
    """
    Local Phase-5 decision stub for NVDA live runner.

    NOTE:
    - This is a temporary stub to avoid import errors.
    - It returns {} so ensure_phase5_decision_with_default()
      will inject a simple EV-only default.
    """
    return {}


def ensure_phase5_decision_with_default(
    entry_ts: str,
    symbol: str,
    regime: str,
) -> Dict[str, Any]:
    raw: Optional[Dict[str, Any]] = get_phase5_decision_for_trade(
        entry_ts=entry_ts,
        symbol=symbol,
        regime=regime,
    )

    if not raw:
        return {
            "ev": 0.008,
            "ev_band_abs": 1.0,
            "allowed": True,
            "reason": "ev_simple_default",
        }

    ev = raw.get("ev")
    if ev is None:
        raw["ev"] = 0.008
    if raw.get("ev_band_abs") is None:
        raw["ev_band_abs"] = 1.0
    if "allowed" not in raw:
        raw["allowed"] = True
    if "reason" not in raw:
        raw["reason"] = "ev_simple_default"
    return raw


def compute_soft_veto_ev_fields(ev: float, realized_pnl: float) -> Dict[str, Any]:
    """
    Phase-5 NVDA soft EV veto diagnostics (diagnostic only).
    """
    abs_ev = abs(ev)

    # NVDA-specific bands based on EV per trade ~0.008:
    #   Band 0: |EV| <= 0.0062
    #   Band 1: 0.0062 < |EV| <= 0.0184
    #   Band 2: |EV| > 0.0184
    if abs_ev <= NVDA_EV_BAND0_MAX:
        ev_band_abs = 0
    elif abs_ev <= NVDA_EV_BAND1_MAX:
        ev_band_abs = 1
    else:
        ev_band_abs = 2

    ev_gap_abs = abs(ev - realized_pnl)
    ev_vs_realized_paper = ev - realized_pnl
    ev_hit_flag = ev_gap_abs >= NVDA_SOFT_VETO_GAP_THRESHOLD

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


def infer_trend_and_vol_regimes_from_regime_tag(regime: str) -> Dict[str, Any]:
    """
    Lightweight parser for regime string to extract trend + volatility regime.

    Expected tags in regime (case-insensitive):
      - "TREND_UP", "TREND_DOWN", "CHOP"/"RANGE"
      - "HIGHVOL", "LOWVOL"
    Anything else falls back to neutral/medium.
    """
    regime_up = (regime or "").upper()

    trend = "neutral"
    if "TREND_UP" in regime_up:
        trend = "up"
    elif "TREND_DOWN" in regime_up:
        trend = "down"
    elif "CHOP" in regime_up or "RANGE" in regime_up:
        trend = "chop"

    vol = "medium"
    if "HIGHVOL" in regime_up:
        vol = "high"
    elif "LOWVOL" in regime_up:
        vol = "low"

    return {
        "trend": trend,
        "vol": vol,
    }


def build_orb_vwap_features_for_nvda(
    symbol: str,
    regime: str,
    side: str,
    realized_pnl: float,
) -> OrbVwapFeatures:
    """
    NVDA-specific ORB+VWAP feature builder that:
      - Boosts orb_strength when trend + side align.
      - Penalizes orb_strength in chop.
      - Uses regime tags for vol_bucket.
    """
    side_u = side.upper()
    regime_info = infer_trend_and_vol_regimes_from_regime_tag(regime)
    trend = regime_info["trend"]
    vol = regime_info["vol"]

    # Base orb strength by side
    base_orb = 0.6 if side_u == "BUY" else 0.3

    # Trend-aligned boost / chop penalty
    if trend == "up" and side_u == "BUY":
        orb_strength = base_orb + 0.1
    elif trend == "down" and side_u == "SELL":
        orb_strength = base_orb + 0.1
    elif trend == "chop":
        orb_strength = base_orb - 0.1
    else:
        orb_strength = base_orb

    # Clamp into a reasonable band
    if orb_strength < 0.1:
        orb_strength = 0.1
    if orb_strength > 0.9:
        orb_strength = 0.9

    # Still stubby, but structured:
    above_vwap = True if side_u == "BUY" else False

    if trend == "up":
        trend_score = 0.5
    elif trend == "down":
        trend_score = -0.5
    elif trend == "chop":
        trend_score = -0.2
    else:
        trend_score = 0.0

    # vol_bucket is a string as expected by OrbVwapFeatures
    vol_bucket = vol  # "low" | "medium" | "high"

    return OrbVwapFeatures(
        orb_strength=orb_strength,
        above_vwap=above_vwap,
        trend_score=trend_score,
        vol_bucket=vol_bucket,
    )


def append_nvda_phase5_paper_entry(
    ts: str,
    symbol: str,
    regime: str,
    side: str,
    price: float,
    result: Dict[str, Any],
    phase5_decision: Dict[str, Any],
) -> None:
    """
    Append a single NVDA Phase-5 paper entry to nvda_phase5_paperlive_results.jsonl,
    enriched with soft EV diagnostics, EV-band hard veto suggestion, and
    ORB+VWAP model EV (ev_orb_vwap_model, log-only).

    This is NVDA-specific and *does not* change any trade gating behavior.
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
    kelly_suggested_qty = compute_phase5_nvda_kelly_qty(
        price=price,
        ev=ev,
    )
    try:
        qty_used = float(result.get("size", result.get("qty", 0.0)) or 0.0)
    except (TypeError, ValueError):
        qty_used = 0.0

    soft_fields = compute_soft_veto_ev_fields(ev=ev, realized_pnl=realized_pnl)

    # Hard-veto suggestion (log-only) using EV-band helper
    hard_result = evaluate_ev_band_hard_veto(
        ev=ev,
        realized_pnl=realized_pnl,
        ev_gap_abs=soft_fields.get("ev_gap_abs"),
        gap_threshold=NVDA_HARD_VETO_GAP_THRESHOLD,
    )

    # Very simple ORB+VWAP features for now:
    # - orb_strength: slightly higher for BUY than SELL
    # - above_vwap: assume True for BUY, False for SELL (to be refined later)
    # - trend_score: neutral for now
    # - vol_bucket: "medium" for now
    orb_strength = 0.6 if side.upper() == "BUY" else 0.3
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

    # Log-only effective EV blend (Phase-5 EV + ORB+VWAP model EV)
    ev_effective_orb_vwap = compute_effective_ev(
        ev_phase5=ev,
        ev_model=ev_orb_vwap_model,
    )

    entry: Dict[str, Any] = {
        "ts": ts,
        "symbol": symbol,
        "regime": regime,
        "side": side,
        "price": price,
        "qty_used": qty_used,
        "kelly_suggested_qty": kelly_suggested_qty,
        "realized_pnl_paper": realized_pnl,
        "ev": ev,
        "phase5_allowed": phase5_allowed,
        "phase5_reason": phase5_reason,
    }
    entry.update(soft_fields)

    entry["ev_hard_veto"] = hard_result.hard_veto
    entry["ev_hard_veto_reason"] = hard_result.hard_veto_reason
    entry["ev_hard_veto_gap_abs"] = hard_result.ev_gap_abs
    entry["ev_hard_veto_gap_threshold"] = hard_result.gap_threshold

    # ORB+VWAP model EV (log-only)
    entry["ev_orb_vwap_model"] = ev_orb_vwap_model
    # Effective EV blend (log-only)
    entry["ev_effective_orb_vwap"] = ev_effective_orb_vwap

    NVDA_PAPER_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with NVDA_PAPER_JSONL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def compute_phase5_nvda_kelly_qty(
    price: float,
    ev: float,
) -> float:
    """
    Simple R-based position sizing helper for NVDA Phase-5.

    - Uses env HAT_PHASE5_RISK_PER_TRADE as $ risk per trade (default 50.0).
    - Assumes a 1% stop (can be refined later).
    - Does NOT change behavior unless HAT_PHASE5_USE_KELLY_QTY=1 is set.
    """
    try:
        risk_per_trade = float(os.environ.get("HAT_PHASE5_RISK_PER_TRADE", "50.0"))
    except (TypeError, ValueError):
        risk_per_trade = 50.0

    # Basic guardrails
    if price <= 0:
        return 1.0
    stop_fraction = 0.01
    stop_dollars = max(price * stop_fraction, 0.01)

    qty = risk_per_trade / stop_dollars

    # Clamp qty into a small, safe band for now
    if qty < 1.0:
        qty = 1.0
    if qty > 100.0:
        qty = 100.0
    return qty


def build_live_config() -> Dict[str, Any]:
    return {
        "dry_run": False,
        "phase5_no_averaging_down_enabled": True,
        "phase5": {
            "no_averaging_down_enabled": True,
            "account_daily_loss_cap": get_account_daily_loss_cap_from_env(50.0),
        },
        "broker": {
            "adapter": "ib",
            "host": os.environ.get("HAT_IB_HOST", "127.0.0.1"),
            "port": int(os.environ.get("HAT_IB_PORT", "7497")),
            "client_id": int(os.environ.get("HAT_IB_CLIENT_ID", "42")),
            "account": os.environ.get("HAT_IB_ACCOUNT", "DUXXXXXXXX"),
            "paper": True,
        },
        "universe": ["NVDA"],
        "costs": {
            "mode": "simple_bps",
            "commission_bps": 0.5,
            "slippage_bps": 1.0,
        },
    }


def main() -> None:
    cfg = build_live_config()

    print("=== nvda_phase5_live_runner ===")
    print("Config:", cfg)

    account_cap = cfg.get("phase5", {}).get("account_daily_loss_cap", 0.0)
    daily_gate = account_daily_loss_gate(
        account_realized_pnl=0.0,
        account_daily_loss_cap=account_cap,
    )
    if not daily_gate.allowed:
        print("\n[PHASE5] Account daily loss gate BLOCKED at start of runner:")
        print("  reason =", daily_gate.reason)
        print("  details=", getattr(daily_gate, "details", None))
        return

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

    symbol = "NVDA"
    side = "BUY"
    qty = 1.0
    price = 1.0
    regime = "NVDA_BPLUS_LIVE"

    ipo_tags = load_ipo_tags()
    ipo_info = ipo_tags.get(symbol.upper())
    if ipo_info:
        print("\n[IPO] Tags for", symbol, ":")
        print("  origin_region    =", ipo_info.get("origin_region"))
        print("  is_hk_origin     =", ipo_info.get("is_hk_origin"))
        print("  is_international =", ipo_info.get("is_international"))
        print("  phase5_candidate =", ipo_info.get("phase5_candidate"))
        print("  phase5_notes     =", ipo_info.get("phase5_notes"))

    phase5_decision = ensure_phase5_decision_with_default(
        entry_ts=entry_ts,
        symbol=symbol,
        regime=regime,
    )

    print("\nCalling place_order_phase5_with_logging(...)")
    print("  symbol   =", symbol)
    print("  entry_ts =", entry_ts)
    print("  side     =", side)
    print("  qty      =", qty)
    print("  regime   =", regime)
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
        append_nvda_phase5_paper_entry(
            ts=entry_ts,
            symbol=symbol,
            regime=regime,
            side=side,
            price=price,
            result=result,
            phase5_decision=phase5_decision,
        )
        print("\n[PHASE5/NVDA] Appended soft+hard EV + ORB+VWAP EV entry to", NVDA_PAPER_JSONL_PATH)
    except Exception as e:
        print("\n[WARN] Failed to append NVDA paper entry:", e)

    import os as _os
    if _os.environ.get("HAT_PHASE5_DOUBLE_BUY_DEMO") == "1":
        print("\n[Phase5] Calling SECOND place_order_phase5_with_logging(...) to demo no-averaging-down")
        result2 = place_order_phase5_with_logging(
            engine,
            symbol=symbol,
            entry_ts=entry_ts,
            side=side,
            qty=qty,
            price=price,
            regime=regime,
            phase5_decision=phase5_decision,
        )
        print("\n[Phase5] Result from SECOND place_order_phase5_with_logging:")
        print(result2)
    print("\nIf wiring is correct, you should see a new event in:")
    print("  logs/phase5_live_events.jsonl")
    print("and, if paper_exec_logger.log_phase5_event/log_event exists,")
    print("  it will also be forwarded there.")
    print("\nAdditionally, NVDA Phase-5 soft + hard EV + ORB+VWAP EV diagnostics will be appended in:")
    print(f"  {NVDA_PAPER_JSONL_PATH}")
    print("\nTo move from small IB paper probe -> fuller live setup:")
    print("  - replace dummy price/qty with real signal- and Kelly-driven values")
    print("  - extend cfg['broker'] / cfg['costs'] / universe as needed")
    print("  - keep this runner under Phase-5 risk + PreMarket guardrails")
if __name__ == "__main__":
    main()
