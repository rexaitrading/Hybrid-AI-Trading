"""
Utility: append paper trade executions to logs/paper_execs.jsonl.

This does NOT place orders or manage risk; it only logs a dict snapshot.
Call log_paper_exec(...) from your paper trading path after a fill occurs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union


# Relative to project root; assumes cwd is repo root when running.
LOG_PATH = Path("logs") / "paper_execs.jsonl"


@dataclass
class PaperExecRecord:
    ts_trade: str
    symbol: str
    side: str
    qty: float
    entry_px: float

    exit_px: Optional[float] = None
    pnl_pct: Optional[float] = None
    regime: Optional[str] = None
    session: Optional[str] = None
    account: Optional[str] = None
    source: str = "paper"
    ts_logged: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if not d.get("ts_logged"):
            d["ts_logged"] = datetime.now(timezone.utc).isoformat()
        # Drop None values to keep JSON lean
        return {k: v for k, v in d.items() if v is not None}


def _ensure_log_dir() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def log_paper_exec(record: Union[PaperExecRecord, Mapping[str, Any]]) -> None:
    """
    Append a single paper execution record to logs/paper_execs.jsonl.

    Parameters
    ----------
    record:
        Either a PaperExecRecord or a mapping with keys like:
        ts_trade, symbol, side, qty, entry_px, exit_px, pnl_pct, regime, session, account, source.
    """
    try:
        if isinstance(record, PaperExecRecord):
            payload = record.to_dict()
        else:
            payload = dict(record)
            payload.setdefault("ts_logged", datetime.now(timezone.utc).isoformat())
            payload.setdefault("source", "paper")

        _ensure_log_dir()
        # Always UTF-8, append one JSON object per line
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\\n")
    except Exception as exc:
        # We never want logging failures to break trading; just warn to stdout.
        print(f"[WARN] log_paper_exec failed: {exc}")
# === Phase 5: paper exec logger helper ======================================

from datetime import datetime, timezone
from pathlib import Path as _Path
import json as _json

_PHASE5_LOGS_DIR = _Path("logs")
_PHASE5_LOGS_DIR.mkdir(parents=True, exist_ok=True)
_PHASE5_LOG_PATH = _PHASE5_LOGS_DIR / "phase5_paper_exec.jsonl"


def log_phase5_exec(
    *,
    ts_trade: str | None,
    symbol: str,
    side: str,
    qty: float,
    entry_px: float,
    regime: str | None = None,
    gate_score_v2: float | None = None,
    kelly_f: float | None = None,
    source: str = "phase5_mock",
) -> None:
    """
    Lightweight Phase 5 execution logger.

    Writes a single JSONL record to logs/phase5_paper_exec.jsonl with the
    key fields you care about for NVDA/ORB Phase 5 validation:

        ts_trade       : ISO8601 UTC timestamp (auto-filled if None)
        symbol         : e.g. "NVDA"
        side           : "BUY" / "SELL"
        qty            : float quantity
        entry_px       : fill price
        regime         : strategy/regime tag, e.g. "NVDA_BPLUS_REPLAY"
        gate_score_v2  : optional GateScore value at decision time
        kelly_f        : optional Kelly fraction used for sizing
        source         : default "phase5_mock" (runner identifier)

    This helper is intentionally independent of the higher-level
    PaperExecRecord so that Phase 5 experiments can proceed without
    impacting existing tests or log formats.
    """
    try:
        if ts_trade is None:
            ts_trade = datetime.now(timezone.utc).isoformat()

        payload = {
            "ts_trade": ts_trade,
            "symbol": symbol,
            "side": side,
            "qty": float(qty),
            "entry_px": float(entry_px),
            "regime": regime,
            "gate_score_v2": float(gate_score_v2) if gate_score_v2 is not None else None,
            "kelly_f": float(kelly_f) if kelly_f is not None else None,
            "source": source,
        }

        with _PHASE5_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(_json.dumps(payload, ensure_ascii=False) + "\\n")
    except Exception as exc:  # pragma: no cover
        # Fail open: we never want logging failure to break trading simulations.
        try:
            import logging as _logging
            _logging.getLogger("hybrid_ai_trading.utils.paper_exec_logger").error(
                "Phase5 log_phase5_exec failed: %s", exc, exc_info=True
            )
        except Exception:
            pass

# === End Phase 5 paper exec helper ==========================================