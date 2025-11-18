from __future__ import annotations

from pathlib import Path
from typing import Optional

from hybrid_ai_trading.qos.provider_qos import ProviderQosLedger, Provider


def log_ibkr_tick(
    symbol: str,
    latency_ms: Optional[float],
    freshness_ms: Optional[float],
    ok: bool = True,
    error: Optional[str] = None,
    op: str = "tick",
) -> None:
    """
    Phase-8 helper: call this from your IBKR data client on each tick / snapshot.

    Example location:
        - inside your tick handler where you know symbol + timing info.
    """
    try:
        root = Path(__file__).resolve().parents[3]  # repo root
        ledger = ProviderQosLedger(str(root))
        if ok:
            ledger.mark_ok(
                provider=Provider.IBKR,
                op=op,
                latency_ms=latency_ms,
                freshness_ms=freshness_ms,
                symbol=symbol,
            )
        else:
            ledger.mark_error(
                provider=Provider.IBKR,
                op=op,
                error=error or "unknown",
                symbol=symbol,
            )
    except Exception:
        # QoS logging must never break data client
        import traceback as _tb
        _tb.print_exc()