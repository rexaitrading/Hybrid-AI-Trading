from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class RiskPulse:
    ts_ns: int
    eq_curve: float          # current equity / balance
    day_pnl: float           # realized day PnL
    open_pnl: float          # unrealized
    max_dd: float            # max intraday drawdown
    daily_loss_cap_remaining: float
    kelly_f: float
    exposure_notional: float
    hedge_status: str        # e.g. "none", "oanda_hedged", "ibkr_fx"
    regime: Optional[str] = None
    provider_primary: Optional[str] = None
    provider_fallback: Optional[str] = None
    latency_ms_primary: Optional[float] = None
    latency_ms_fallback: Optional[float] = None
    violations: Optional[str] = None  # comma-separated flags

    @classmethod
    def now(
        cls,
        eq_curve: float,
        day_pnl: float,
        open_pnl: float,
        max_dd: float,
        daily_loss_cap_remaining: float,
        kelly_f: float,
        exposure_notional: float,
        hedge_status: str,
        regime: Optional[str] = None,
        provider_primary: Optional[str] = None,
        provider_fallback: Optional[str] = None,
        latency_ms_primary: Optional[float] = None,
        latency_ms_fallback: Optional[float] = None,
        violations: Optional[str] = None,
    ) -> "RiskPulse":
        return cls(
            ts_ns=time.time_ns(),
            eq_curve=eq_curve,
            day_pnl=day_pnl,
            open_pnl=open_pnl,
            max_dd=max_dd,
            daily_loss_cap_remaining=daily_loss_cap_remaining,
            kelly_f=kelly_f,
            exposure_notional=exposure_notional,
            hedge_status=hedge_status,
            regime=regime,
            provider_primary=provider_primary,
            provider_fallback=provider_fallback,
            latency_ms_primary=latency_ms_primary,
            latency_ms_fallback=latency_ms_fallback,
            violations=violations,
        )


class RiskTelemetryWriter:
    def __init__(self, root: str) -> None:
        self._root = root
        self._path = os.path.join(root, ".intel", "risk_pulse.jsonl")
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

    def write(self, pulse: RiskPulse) -> None:
        line = json.dumps(asdict(pulse), separators=(",", ":"))
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(line + "\n")