from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any, Dict, List, Optional


DEFAULT_STATUS_PATH = Path("logs") / "blockg_status_stub.json"


@dataclass(frozen=True)
class BlockGStatus:
    as_of_date: str
    nvda_blockg_ready: bool
    # Core daily requirements
    phase4_ok_today: bool = False
    ev_hard_daily_ok_today: bool = False
    gatescore_fresh_today: bool = False
    gatescore_value: float = 0.0
    gatescore_min_required: float = 0.0
    gatescore_samples: int = 0
    gatescore_min_samples: int = 0
    gatescore_samples_ok: bool = False
    reasons_not_ready: List[str] = None  # type: ignore[assignment]


def _get_bool(d: Dict[str, Any], k: str, default: bool = False) -> bool:
    v = d.get(k, default)
    return bool(v)


def _get_int(d: Dict[str, Any], k: str, default: int = 0) -> int:
    v = d.get(k, default)
    try:
        return int(v)
    except Exception:
        return default


def _get_float(d: Dict[str, Any], k: str, default: float = 0.0) -> float:
    v = d.get(k, default)
    try:
        return float(v)
    except Exception:
        return default


def load_blockg_status(path: Optional[str] = None) -> BlockGStatus:
    p = Path(path) if path else DEFAULT_STATUS_PATH
    raw = p.read_text(encoding="utf-8-sig")
    d = json.loads(raw)

    reasons = d.get("reasons_not_ready", [])
    if not isinstance(reasons, list):
        reasons = [str(reasons)]

    return BlockGStatus(
        as_of_date=str(d.get("as_of_date", "")),
        nvda_blockg_ready=_get_bool(d, "nvda_blockg_ready", False),
        phase4_ok_today=_get_bool(d, "phase4_ok_today", False),
        ev_hard_daily_ok_today=_get_bool(d, "ev_hard_daily_ok_today", False),
        gatescore_fresh_today=_get_bool(d, "gatescore_fresh_today", False),
        gatescore_value=_get_float(d, "gatescore_value", 0.0),
        gatescore_min_required=_get_float(d, "gatescore_min_required", 0.0),
        gatescore_samples=_get_int(d, "gatescore_samples", 0),
        gatescore_min_samples=_get_int(d, "gatescore_min_samples", 0),
        gatescore_samples_ok=_get_bool(d, "gatescore_samples_ok", False),
        reasons_not_ready=[str(x) for x in reasons],
    )


def nvda_blockg_ready(status: BlockGStatus) -> bool:
    return bool(status.nvda_blockg_ready)


def explain_not_ready(status: BlockGStatus) -> List[str]:
    # Prefer explicit reasons from builder; otherwise compute minimal diagnostics.
    if status.reasons_not_ready:
        return list(status.reasons_not_ready)

    reasons: List[str] = []
    if not status.phase4_ok_today:
        reasons.append("phase4_ok_today=false")
    if not status.ev_hard_daily_ok_today:
        reasons.append("ev_hard_daily_ok_today=false")
    if not status.gatescore_fresh_today:
        reasons.append("gatescore_fresh_today=false")
    if status.gatescore_value < status.gatescore_min_required:
        reasons.append("gatescore_below_threshold")
    if not status.gatescore_samples_ok:
        reasons.append("gatescore_samples_not_ok")
    return reasons
def ensure_symbol_blockg_ready(
    *,
    symbol: str,
    status_path: Optional[str] = None,
    allow_paper: bool = True,
    is_paper: Optional[bool] = None,
) -> BlockGStatus:
    """
    Fail-closed gate used by execution path.
    - If is_paper is True and allow_paper is True: bypass.
    - Otherwise require contract readiness for symbol.
    """
    if is_paper is True and allow_paper:
        return load_blockg_status(status_path)

    s = load_blockg_status(status_path)

    sym = (symbol or "").upper().strip()
    ok = False
    if sym == "NVDA":
        ok = bool(s.nvda_blockg_ready)
    else:
        # fail-closed for unknown symbols until explicitly added to contract
        ok = False

    if ok:
        return s

    reasons = explain_not_ready(s)
    msg = f"BLOCK-G NOT READY symbol={sym} date={s.as_of_date} reasons={reasons}"
    raise RuntimeError(msg)