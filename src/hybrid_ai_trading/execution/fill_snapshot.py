from __future__ import annotations

from typing import Any, Dict, Optional


def slippage_bps(expected_px: float, actual_px: float) -> float:
    if expected_px <= 0:
        return 0.0
    return (actual_px - expected_px) / expected_px * 10000.0


def slippage_abs(expected_px: float, actual_px: float) -> float:
    return actual_px - expected_px


def make_slippage_event(
    *,
    ts: str,
    symbol: str,
    side: str,
    qty: float,
    expected_px: float,
    actual_px: float,
    broker: str = "",
    strategy: str = "",
    order_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ev: Dict[str, Any] = {
        "ts": ts,
        "symbol": symbol,
        "side": side,
        "qty": float(qty),
        "expected_px": float(expected_px),
        "actual_px": float(actual_px),
        "slip_abs": float(slippage_abs(expected_px, actual_px)),
        "slip_bps": float(slippage_bps(expected_px, actual_px)),
        "broker": broker or "",
        "strategy": strategy or "",
        "order_id": order_id,
    }
    if extra:
        ev["extra"] = extra
    return ev
