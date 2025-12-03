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

from hybrid_ai_trading.risk.phase5_ev_band_hard_veto import evaluate_ev_band_hard_veto

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


def get_phase5_decision_for_trade(
    symbol: Optional[str] = None,
    entry_ts: Optional[str] = None,
    symbol_code: Optional[str] = None,
    ts: Optional[str] = None,
    **_: Any,
) -> Optional[Dict[str, Any]]:
    """
    Backward-compatible shim used by existing Phase-5 tools (e.g. nvda_phase5_live_smoke).

    Accepts both:
      get_phase5_decision_for_trade("NVDA", "2025-...")
      get_phase5_decision_for_trade(symbol="NVDA", entry_ts="2025-...")
      get_phase5_decision_for_trade(symbol_code="NVDA", ts="2025-...")
    And ignores any extra keyword arguments (e.g. regime=...).

    Returns the underlying decision dict for (symbol, ts), or None if no match.
    """
    sym = symbol_code or symbol
    ts_value = entry_ts or ts
    if sym is None or ts_value is None:
        return None

    decision = lookup_decision_by_ts(sym, entry_ts=str(ts_value))
    if decision is None:
        return None

    return decision.raw
def attach_ev_band_hard_veto(decision, realized_pnl=None, gap_threshold=0.7):
    """
    Log-only helper to attach EV-band hard veto suggestion into a Phase-5 decision dict.

    This does NOT block trades. It only enriches the decision mapping with:
        - ev_hard_veto: bool
        - ev_hard_veto_reason: str or None
        - ev_hard_veto_gap_abs: float
        - ev_hard_veto_gap_threshold: float

    Callers may choose to:
        - log these fields,
        - push them to Notion,
        - or, later, treat hard_veto=True as a real gate under a config flag.
    """
    if decision is None:
        decision = {}

    # Extract EV and realized PnL; fall back to 0.0
    ev = float(decision.get("ev") or 0.0)

    if realized_pnl is None:
        # prefer realized_pnl_paper, then realized_pnl if present on the decision
        if "realized_pnl_paper" in decision:
            try:
                realized_pnl = float(decision.get("realized_pnl_paper") or 0.0)
            except (TypeError, ValueError):
                realized_pnl = 0.0
        elif "realized_pnl" in decision:
            try:
                realized_pnl = float(decision.get("realized_pnl") or 0.0)
            except (TypeError, ValueError):
                realized_pnl = 0.0
        else:
            realized_pnl = 0.0

    # Existing ev_gap_abs if present on the decision
    ev_gap_abs = None
    if "ev_gap_abs" in decision and decision.get("ev_gap_abs") is not None:
        try:
            ev_gap_abs = float(decision.get("ev_gap_abs"))
        except (TypeError, ValueError):
            ev_gap_abs = None

    result = evaluate_ev_band_hard_veto(
        ev=ev,
        realized_pnl=realized_pnl,
        ev_gap_abs=ev_gap_abs,
        gap_threshold=gap_threshold,
    )

    decision["ev_hard_veto"] = result.hard_veto
    decision["ev_hard_veto_reason"] = result.hard_veto_reason
    decision["ev_hard_veto_gap_abs"] = result.ev_gap_abs
    decision["ev_hard_veto_gap_threshold"] = result.gap_threshold

    return decision