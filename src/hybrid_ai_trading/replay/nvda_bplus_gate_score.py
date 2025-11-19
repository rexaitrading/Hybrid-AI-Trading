"""
NVDA B+ GateScore helpers for ORB + VWAP micro-mode.

This module is intentionally narrow:
- It operates on a single trade dict (e.g. loaded from replay JSONL, or a row object converted to dict).
- It returns simple floats that can later be:
  - Written into Notion,
  - Used by the risk manager,
  - Or used in offline evaluation.

NOTE:
These formulas are intentionally simple and will be tuned once we have more
replay data. They are meant as a starting point, not a final model.
"""

from __future__ import annotations

from typing import Dict, Any
from hybrid_ai_trading.cost_model import CostInputs, estimate_cost


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def compute_gate_score_v2(trade: Dict[str, Any]) -> float:
    """
    Compute a simple GateScore v2 for a single trade.

    Inputs (from trade dict):
      - r_multiple      (float)
      - gross_pnl_pct   (float)

    Current heuristic:
      score = w_r * r_multiple + w_p * gross_pnl_pct + bias

    where:
      - w_r > 0 rewards higher R-multiple
      - w_p > 0 rewards higher percentage PnL
      - losing trades (r_multiple < 0 or gross_pnl_pct < 0) get clipped down

    This is deliberately simple. We will tune the weights once we have a
    larger replay sample.
    """
    r_multiple = _safe_float(trade.get("r_multiple", 0.0))
    gross_pnl_pct = _safe_float(trade.get("gross_pnl_pct", 0.0))

    # Weights  tweak later based on replay stats
    w_r = 0.5
    w_p = 5.0  # 0.8% => 0.008 * 5 = 0.04
    bias = 0.0

    score = w_r * r_multiple + w_p * gross_pnl_pct + bias

    # Optional clipping: prevent outliers from exploding
    # (keep in a modest band around zero; tune later)
    if score > 1.0:
        score = 1.0
    elif score < -1.0:
        score = -1.0

    return score


def compute_ev_from_trade(trade: Dict[str, Any]) -> float:
    """
    Compute an expected value estimate from a single trade, adjusted for estimated
    execution cost.

    By default we compute:
        ev = gross_pnl_pct - cost_fraction

    where:
        - gross_pnl_pct is the realized gross PnL percentage (e.g. 0.008 = +0.8%)
        - cost_fraction is total_cost / notional, using the CostInputs / estimate_cost
          helper and env-based defaults for slippage/fees.

    If we cannot infer a sensible mid_price and quantity from the trade dict,
    we fall back to:
        ev = gross_pnl_pct
    """
    gross_pnl_pct = _safe_float(trade.get("gross_pnl_pct", 0.0))

    try:
        symbol = str(trade.get("symbol") or "NVDA")
        side = (str(trade.get("side") or trade.get("direction") or "BUY")).upper()

        mid_price = _safe_float(
            trade.get("entry_px")
            or trade.get("entry_price")
            or trade.get("fill_px")
            or trade.get("fill_price"),
            0.0,
        )
        qty = _safe_float(
            trade.get("qty")
            or trade.get("quantity")
            or trade.get("shares"),
            0.0,
        )

        cost_fraction = 0.0
        if mid_price > 0.0 and qty > 0.0:
            ci = CostInputs(
                symbol=symbol,
                side=side,
                mid_price=mid_price,
                qty=qty,
                spread=None,
                fee_per_share=None,
                fee_rate_bp=None,
                expected_slippage_bp=None,
            )
            cb = estimate_cost(ci)
            notional = cb.notional
            if notional > 0.0:
                cost_fraction = cb.total_cost / notional
    except Exception:
        cost_fraction = 0.0

    ev = gross_pnl_pct - cost_fraction
    return ev

def passes_micro_gate(trade: Dict[str, Any], min_gate_score: float = 0.04) -> bool:
    """
    Micro-mode gate for NVDA B+ trades.

    A trade passes the gate if its gate_score_v2 is greater than or equal
    to the configured minimum.

    Rules:
      - If trade["gate_score_v2"] is present, use it directly.
      - If missing, try to recompute via compute_gate_score_v2(trade).
      - On any error, fail closed (return False).
    """
    try:
        score = trade.get("gate_score_v2", None)
    except Exception:
        score = None

    if score is None:
        try:
            score = compute_gate_score_v2(trade)
        except Exception:
            return False

    try:
        return float(score) >= float(min_gate_score)
    except Exception:
        return False



