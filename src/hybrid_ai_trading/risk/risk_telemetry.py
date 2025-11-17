from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class RiskPulse:
    """
    Generic risk snapshot for telemetry.

    Fields are intentionally optional so callers can send partial info.
    """

    ts_utc: str
    eq_curve: Optional[float] = None
    day_pnl: Optional[float] = None
    open_pnl: Optional[float] = None
    max_dd: Optional[float] = None
    daily_loss_cap_remaining: Optional[float] = None
    kelly_f: Optional[float] = None
    exposure_notional: Optional[float] = None
    hedge_status: Optional[str] = None
    regime: Optional[Any] = None
    provider_primary: Optional[str] = None
    provider_fallback: Optional[str] = None
    latency_ms_primary: Optional[float] = None
    latency_ms_fallback: Optional[float] = None
    violations: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None

    @classmethod
    def now(cls, **kwargs: Any) -> "RiskPulse":
        """
        Construct a pulse with current UTC timestamp.

        All other fields are passed via kwargs and remain optional.
        """
        ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        return cls(ts_utc=ts, **kwargs)


class RiskTelemetryWriter:
    """
    Simple JSONL writer for RiskPulse snapshots.

    Default location:
        <repo_root>/.intel/risk_pulse.jsonl

    Best-effort only: all write errors are logged as WARN and swallowed.
    """

    def __init__(self, root: Optional[str] = None) -> None:
        if root is None:
            # risk/risk_telemetry.py -> up 3 levels: src/hybrid_ai_trading/risk -> src/hybrid_ai_trading -> src -> repo root
            root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        self._root = root
        intel_dir = os.path.join(self._root, ".intel")
        os.makedirs(intel_dir, exist_ok=True)
        self._path = os.path.join(intel_dir, "risk_pulse.jsonl")

    def write(self, pulse: RiskPulse) -> None:
        try:
            line = json.dumps(asdict(pulse), ensure_ascii=False)
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as exc:  # noqa: BLE001
            # ASCII-only to avoid console encoding issues
            print(
                "[risk_telemetry] WARN: failed to write risk pulse:",
                str(exc),
                file=sys.stderr,
            )