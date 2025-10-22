from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class RiskDecision:
    status: str  # "ok" or "block"
    reason: str = ""
    meta: Dict[str, Any] | None = None

def max_order_size(symbol: str, qty: float, asset: str, limits: Dict[str, float]) -> RiskDecision:
    """
    Enforce per-asset-class max size. Example limits:
      {"equity": 2000, "crypto": 5, "forex": 200000}
    """
    cap = limits.get(asset.lower())
    if cap is None:
        return RiskDecision("ok")
    if qty > cap:
        return RiskDecision("block", f"max_order_size_exceeded cap={cap}", {"qty": qty, "asset": asset})
    return RiskDecision("ok")

def daily_pnl_cap(current_pnl: float, cap_abs: float | None) -> RiskDecision:
    """Blocks if daily loss exceeds cap_abs (absolute)."""
    if cap_abs is None:
        return RiskDecision("ok")
    if current_pnl <= -abs(cap_abs):
        return RiskDecision("block", f"daily_loss_cap {current_pnl} <= -{cap_abs}", {"pnl": current_pnl})
    return RiskDecision("ok")

def drawdown_cap(equity: float, peak_equity: float, dd_max: float | None) -> RiskDecision:
    """Blocks if drawdown exceeds dd_max (0..1)."""
    if dd_max is None or peak_equity <= 0:
        return RiskDecision("ok")
    dd = 1.0 - (equity / peak_equity)
    if dd > dd_max:
        return RiskDecision("block", f"drawdown_breach dd={dd:.4f} > {dd_max}", {"equity": equity, "peak": peak_equity})
    return RiskDecision("ok")

def latency_killswitch(ms: float, threshold_ms: float | None) -> RiskDecision:
    if threshold_ms is None:
        return RiskDecision("ok")
    if ms > threshold_ms:
        return RiskDecision("block", f"latency_killswitch {ms:.1f}ms > {threshold_ms}ms", {"latency_ms": ms})
    return RiskDecision("ok")

def partial_age_killswitch(age_sec: float, max_age_sec: float | None) -> RiskDecision:
    if max_age_sec is None:
        return RiskDecision("ok")
    if age_sec > max_age_sec:
        return RiskDecision("block", f"partial_age_killswitch {age_sec:.1f}s > {max_age_sec}s", {"age_sec": age_sec})
    return RiskDecision("ok")
