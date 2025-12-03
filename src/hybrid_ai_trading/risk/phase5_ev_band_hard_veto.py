from __future__ import annotations

"""
Phase-5 EV-band hard veto helper (log-only, NVDA/SPY/QQQ shared).

This module centralizes a simple, explicit rule for suggesting when a trade
*would* be a hard veto based on EV and realized PnL:

    - If EV < 0.0            -> candidate hard veto ("ev<0")
    - Else if |EV - PnL| >= gap_threshold (default 0.7R) -> candidate hard veto ("ev_gap>=threshold")

IMPORTANT:
- This is currently intended for logging, reporting, and offline diagnostics.
- It MUST NOT directly block trades until the caller explicitly opts in
  (e.g. via config flags, Phase-5 gating helpers, or risk manager wiring).
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class EvBandHardVetoResult:
    ev: float
    realized_pnl: float
    ev_gap_abs: float
    gap_threshold: float
    hard_veto: bool
    hard_veto_reason: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ev": self.ev,
            "realized_pnl": self.realized_pnl,
            "ev_gap_abs": self.ev_gap_abs,
            "gap_threshold": self.gap_threshold,
            "hard_veto": self.hard_veto,
            "hard_veto_reason": self.hard_veto_reason,
        }


def evaluate_ev_band_hard_veto(
    ev: float,
    realized_pnl: Optional[float] = None,
    ev_gap_abs: Optional[float] = None,
    gap_threshold: float = 0.7,
) -> EvBandHardVetoResult:
    """
    Evaluate a simple EV-band-based hard-veto *suggestion*.

    Parameters
    ----------
    ev : float
        Expected value (R-units or other normalized EV).
    realized_pnl : float, optional
        Realized PnL for the trade. If missing, defaults to 0.0 for the
        purpose of computing ev_gap_abs.
    ev_gap_abs : float, optional
        Absolute EV-vs-realized gap. If not provided, computed as
        abs(ev - realized_pnl).
    gap_threshold : float, default 0.7
        Threshold for marking a trade as a hard-veto candidate based on
        EV-vs-realized gap.

    Returns
    -------
    EvBandHardVetoResult
        Dataclass with EV, realized PnL, ev_gap_abs, gap_threshold,
        hard_veto flag and reason string (or None).

    NOTE
    ----
    - This function is *log-only* and must not directly change trade
      gating on its own.
    - Callers (e.g. Phase-5 gating helpers) are responsible for deciding
      when to treat hard_veto=True as a real block vs a diagnostic flag.
    """
    if realized_pnl is None:
        realized_pnl = 0.0

    if ev_gap_abs is None:
        ev_gap_abs = abs(ev - realized_pnl)

    hard_veto = False
    hard_veto_reason: Optional[str] = None

    if ev < 0.0:
        hard_veto = True
        hard_veto_reason = "ev<0"
    elif ev_gap_abs >= gap_threshold:
        hard_veto = True
        hard_veto_reason = "ev_gap>=threshold"

    return EvBandHardVetoResult(
        ev=float(ev),
        realized_pnl=float(realized_pnl),
        ev_gap_abs=float(ev_gap_abs),
        gap_threshold=float(gap_threshold),
        hard_veto=hard_veto,
        hard_veto_reason=hard_veto_reason,
    )