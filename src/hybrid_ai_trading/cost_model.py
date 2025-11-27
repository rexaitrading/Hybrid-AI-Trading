from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class CostInputs:
    """
    Inputs for estimating execution cost for a single trade idea.

    All prices are in absolute price units (e.g. USD per share).
    Quantities are in units (shares / contracts).
    """

    symbol: str
    side: str  # "BUY" or "SELL"

    mid_price: float
    qty: float

    spread: Optional[float] = None           # absolute price units; full bid-ask spread
    fee_per_share: Optional[float] = None    # fee per unit, e.g. $0.005/share
    fee_rate_bp: Optional[float] = None      # basis points of notional
    expected_slippage_bp: Optional[float] = None  # extra slippage over half-spread, in bp


@dataclass
class CostBreakdown:
    """
    Decomposed execution cost (always positive = cost).
    """

    symbol: str
    side: str

    notional: float
    spread_cost: float
    slippage_cost: float
    fee_cost: float

    total_cost: float


def _env_float(name: str, default: float) -> float:
    val = os.environ.get(name)
    if not val:
        return default
    try:
        return float(val)
    except ValueError:
        return default


def estimate_cost(inputs: CostInputs) -> CostBreakdown:
    """
    Estimate total execution cost given basic inputs.

    Components:
        - spread_cost   ~ half-spread * qty
        - slippage_cost ~ expected_slippage_bp * mid_price * qty / 1e4
        - fee_cost      ~ fee_per_share * qty + fee_rate_bp * notional / 1e4

    Notes:
        - All costs are positive numbers (we treat cost as > 0).
        - Defaults can be overridden via env:
            HAT_COST_DEFAULT_SLIPPAGE_BP
            HAT_COST_DEFAULT_FEE_BP
            HAT_COST_DEFAULT_FEE_PER_SHARE
    """
    notional = inputs.mid_price * inputs.qty

    # Spread cost: half of the full spread
    if inputs.spread is not None and inputs.spread > 0.0:
        half_spread = 0.5 * inputs.spread
    else:
        half_spread = 0.0
    spread_cost = half_spread * inputs.qty

    # Slippage cost: additional bp over mid price
    default_slip_bp = _env_float("HAT_COST_DEFAULT_SLIPPAGE_BP", 1.0)  # 1 bp by default
    slip_bp = inputs.expected_slippage_bp if inputs.expected_slippage_bp is not None else default_slip_bp
    slippage_cost = abs(slip_bp) * inputs.mid_price * inputs.qty / 10000.0

    # Fee cost: per-share + basis-point fee
    default_fee_per_share = _env_float("HAT_COST_DEFAULT_FEE_PER_SHARE", 0.0)
    default_fee_bp = _env_float("HAT_COST_DEFAULT_FEE_BP", 0.0)

    fee_per_share = inputs.fee_per_share if inputs.fee_per_share is not None else default_fee_per_share
    fee_rate_bp = inputs.fee_rate_bp if inputs.fee_rate_bp is not None else default_fee_bp

    fee_cost = abs(fee_per_share) * inputs.qty + abs(fee_rate_bp) * notional / 10000.0

    total_cost = spread_cost + slippage_cost + fee_cost

    return CostBreakdown(
        symbol=inputs.symbol,
        side=inputs.side,
        notional=notional,
        spread_cost=spread_cost,
        slippage_cost=slippage_cost,
        fee_cost=fee_cost,
        total_cost=total_cost,
    )


class CostTelemetryWriter:
    """
    JSONL writer for cost estimation snapshots.

    Default location:
        <repo_root>/.intel/cost_model.jsonl

    Best-effort only: errors are swallowed after logging.
    """

    def __init__(self, root: Optional[str] = None) -> None:
        if root is None:
            # cost_model.py -> src/hybrid_ai_trading -> src -> repo root
            root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self._root = root
        intel_dir = os.path.join(self._root, ".intel")
        os.makedirs(intel_dir, exist_ok=True)
        self._path = os.path.join(intel_dir, "cost_model.jsonl")

    def write(self, inputs: CostInputs, breakdown: CostBreakdown) -> None:
        try:
            ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            payload: Dict[str, Any] = {
                "ts_utc": ts,
                "inputs": asdict(inputs),
                "breakdown": asdict(breakdown),
            }
            line = json.dumps(payload, ensure_ascii=False)
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            return


def _is_enabled() -> bool:
    """
    Env gate for cost model telemetry.

    HAT_COST_ENABLE in {"1", "true", "TRUE", "yes", "YES"} enables logging.
    """
    val = os.environ.get("HAT_COST_ENABLE")
    if not val:
        return False
    return val in {"1", "true", "TRUE", "yes", "YES"}


def record_cost(inputs: CostInputs) -> CostBreakdown:
    """
    Convenience helper:

        b = record_cost(
            CostInputs(
                symbol="AAPL",
                side="BUY",
                mid_price=100.0,
                qty=100,
                spread=0.02,
            )
        )

    Returns CostBreakdown and, if enabled, logs to .intel/cost_model.jsonl.
    """
    breakdown = estimate_cost(inputs)

    if _is_enabled():
        writer = CostTelemetryWriter()
        writer.write(inputs, breakdown)

    return breakdown


def has_edge(expected_edge: float, breakdown: CostBreakdown, safety_mult: float = 1.5) -> bool:
    """
    Simple gate: check if expected edge (in PnL units) is comfortably above cost.

    Example:
        if has_edge(expected_edge=25.0, breakdown=cost, safety_mult=2.0):
            # proceed

    expected_edge and total_cost must be in the same currency units.
    """
    threshold = safety_mult * breakdown.total_cost
    return expected_edge >= threshold