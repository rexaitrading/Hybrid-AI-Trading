from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def iso_utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ReplayWindow:
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    start_time_local: str = "09:30:00"
    end_time_local: str = "16:00:00"


@dataclass(frozen=True)
class ReplaySessionArtifact:
    ts_utc: str
    as_of_date: str
    symbol: str
    window: ReplayWindow
    fill_model: str
    latency_model: str
    bars_source: str
    notes: str = ""


@dataclass(frozen=True)
class ReplaySummary:
    ts_utc: str
    as_of_date: str
    symbol: str
    window_start: str
    window_end: str
    trades: int
    gross_pnl: float
    net_pnl: float
    est_fees: float
    est_slippage: float
    model_fill: str
    model_latency: str


def write_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_session_artifact(path: str | Path, art: ReplaySessionArtifact) -> None:
    write_json(path, asdict(art))


def write_summary(path: str | Path, s: ReplaySummary) -> None:
    write_json(path, asdict(s))