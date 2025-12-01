"""
Phase-5 gating helpers.

Central place for:
- Loading Phase-5 decisions JSON (per symbol).
- Looking up whether a trade should be allowed or blocked.
- Matching on timestamp and/or other keys (extensible later).

This module is designed to be used by:
- Mock/demo runners (replay / validation).
- Real engine runners (paper / live Phase-5).
"""

from __future__ import annotations

try:
    # EV-band helper shared between Phase-5 tools and RiskManager
    from hybrid_ai_trading.risk.risk_phase5_ev_bands import require_ev_band
except Exception:  # pragma: no cover - defensive fallback
    require_ev_band = None

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# We can extend this later with additional keys (trade_id, replay_tag, etc.)
TS_KEYS = ["entry_ts", "ts_trade", "ts", "timestamp"]


@dataclass
class Phase5Decision:
    raw: Dict[str, Any]

    @property
    def entry_ts(self) -> str:
        for key in TS_KEYS:
            val = self.raw.get(key)
            if val:
                return str(val)
        return "UNKNOWN_TS"

    @property
    def allow_flag(self) -> bool:
        """Interpret phase5_sim_allow as a boolean."""
        raw_flag = self.raw.get("phase5_sim_allow")

        if isinstance(raw_flag, bool):
            return raw_flag
        if isinstance(raw_flag, (int, float)):
            return raw_flag != 0
        if raw_flag is None:
            # Conservative: missing flag -> blocked (can be relaxed later)
            return False

        s = str(raw_flag).strip().lower()
        if s in ("true", "1", "yes", "y"):
            return True
        if s in ("false", "0", "no", "n"):
            return False

        # Unknown string -> conservative: blocked
        return False


def _find_first_list(obj: Any, depth: int = 0, max_depth: int = 5) -> Optional[List[Any]]:
    """Recursively search for the first list anywhere in the JSON structure."""
    if depth > max_depth:
        return None
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for v in obj.values():
            found = _find_first_list(v, depth + 1, max_depth)
            if found is not None:
                return found
    return None


def _load_raw_decisions(symbol_code: str) -> List[Dict[str, Any]]:
    """
    Low-level: load Phase-5 decisions JSON for a symbol, return list of dict rows.

    Handles:
    - top-level list: [ {...}, {...} ]
    - nested list somewhere inside a dict
    - single dict (treated as one-row list)
    """
    fname = f"{symbol_code.lower()}_phase5_decisions.json"
    path = Path("logs") / fname
    if not path.exists():
        # No decisions file -> treat as "no gating configured"
        return []

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    rows = _find_first_list(data)
    if rows is None:
        if isinstance(data, dict):
            rows = [data]
        else:
            raise SystemExit(
                f"Unexpected JSON shape in {path}, expected a list or a dict representing a single row."
            )

    if not isinstance(rows, list):
        raise SystemExit(
            f"Unexpected JSON shape in {path}, expected rows to be a list."
        )

    # Filter out obviously bad rows
    result: List[Dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            result.append(row)
    return result


# Simple in-process cache so we don't re-read JSON on every order
_DECISION_CACHE: Dict[str, List[Phase5Decision]] = {}


def load_decisions_for_symbol(symbol_code: str) -> List[Phase5Decision]:
    """
    Load and cache Phase-5 decisions for a symbol.

    symbol_code: "NVDA", "SPY", "QQQ", etc.
    """
    key = symbol_code.upper()
    if key in _DECISION_CACHE:
        return _DECISION_CACHE[key]

    raw_rows = _load_raw_decisions(key)
    decisions = [Phase5Decision(raw=row) for row in raw_rows]
    _DECISION_CACHE[key] = decisions
    return decisions


def lookup_decision_by_ts(symbol_code: str, entry_ts: str) -> Optional[Phase5Decision]:
    """
    Find a Phase-5 decision row for given symbol + entry_ts string.

    For now we match on exact string equality.
    Later we can extend to tolerate small time drifts or use trade_id.
    """
    if entry_ts is None:
        return None

    et = str(entry_ts)
    decisions = load_decisions_for_symbol(symbol_code)
    for dec in decisions:
        if dec.entry_ts == et:
            return dec
    return None


def should_allow_trade(
    symbol_code: str,
    entry_ts: Optional[str],
) -> Tuple[bool, Optional[Phase5Decision]]:
    """
    Main helper to call from runners / engine.

    Returns:
        (allow: bool, matched_decision: Optional[Phase5Decision])

    Logic:
    - If there is a matching decision row:
        -> use its allow_flag.
    - If there is no matching decision row:
        -> default to allow = True (no explicit block).
          (This matches the "no mysterious daemon, explicit gate" requirement.)
    """
    if entry_ts is None:
        # Without a timestamp, we have no match key -> default allow
        return True, None

    decision = lookup_decision_by_ts(symbol_code, entry_ts=str(entry_ts))
    if decision is None:
        # No explicit decision row -> allow
        return True, None

    allow = decision.allow_flag
    return allow, decision


def apply_ev_band_to_decision(decision: dict) -> dict:
    """
    Attach EV-band gating info to a Phase-5 decision dict for NVDA/SPY/QQQ.

    This helper is intentionally conservative:

      - It does NOT flip `phase5_allowed`. Your existing Phase-5 guards
        (no-averaging-down, daily caps, etc.) remain the source of truth.

      - It only sets:
            decision["ev_band_allowed"]
            decision["ev_band_reason"]

      - It only acts when:
            decision["regime"] in {"NVDA_BPLUS_LIVE", "SPY_ORB_LIVE", "QQQ_ORB_LIVE"}

      - If `require_ev_band` is unavailable, it records that fact instead of
        raising, so tests and tools keep running.

    This is designed so that JSONL / CSV / Notion can see EV-band status
    without changing live routing decisions yet.
    """
    # Defensive: if module import failed, record the reason and return.
    if "require_ev_band" not in globals() or require_ev_band is None:
        decision.setdefault("ev_band_allowed", None)
        decision.setdefault("ev_band_reason", "ev_band_helper_unavailable")
        return decision

    regime = decision.get("regime")
    ev_val = decision.get("ev")

    # Only annotate for live NVDA/SPY/QQQ Phase-5 regimes.
    if regime not in ("NVDA_BPLUS_LIVE", "SPY_ORB_LIVE", "QQQ_ORB_LIVE"):
        decision.setdefault("ev_band_allowed", None)
        decision.setdefault("ev_band_reason", "ev_band_not_applicable")
        return decision

    # Allow require_ev_band() to enforce presence / band logic.
    try:
        ev_float = None if ev_val is None else float(ev_val)
    except (TypeError, ValueError):
        ev_float = None

    allowed, reason = require_ev_band(regime, ev_float)
    decision["ev_band_allowed"] = allowed
    decision["ev_band_reason"] = reason

    return decision