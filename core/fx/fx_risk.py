from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Any, Optional

from core.fx.oanda_client import OandaFXClient, FXQuote


@dataclass
class FxSnapshot:
    instrument: str
    time: str
    bid: float
    ask: float
    mid: float
    spread: float
    ts_local: float  # epoch seconds when we fetched it


@dataclass
class FxRiskFlags:
    ok: bool
    spread_wide: bool
    stale: bool
    error: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "spread_wide": self.spread_wide,
            "stale": self.stale,
            "error": self.error,
        }


def get_fx_snapshot(instrument: str = "USD_CAD") -> FxSnapshot:
    """
    Fetch a fresh FX snapshot from OANDA practice/live using OandaFXClient.
    """
    client = OandaFXClient()
    q: FXQuote = client.price(instrument)
    return FxSnapshot(
        instrument=q.instrument,
        time=q.time,
        bid=q.bid,
        ask=q.ask,
        mid=q.mid,
        spread=q.spread,
        ts_local=time.time(),
    )


def evaluate_fx_risk(
    snapshot: FxSnapshot,
    max_spread: float = 0.0005,
    max_age_seconds: float = 10.0,
    now: Optional[float] = None,
) -> FxRiskFlags:
    """
    Turn an FxSnapshot into simple risk flags:
      - spread_wide: True if spread > max_spread
      - stale: True if quote older than max_age_seconds (local clock)
      - ok: True only if no flags and no error
    """
    if now is None:
        now = time.time()

    spread_wide = snapshot.spread > max_spread
    age = now - snapshot.ts_local
    stale = age > max_age_seconds

    ok = not spread_wide and not stale

    return FxRiskFlags(
        ok=ok,
        spread_wide=spread_wide,
        stale=stale,
        error=None,
    )