from __future__ import annotations

"""
ORB + VWAP EV model (Phase-5, Block E, log-only skeleton).

This module centralizes a simple, *explicit* EV calculation in R units based on:

- ORB strength (0..1),
- relative location to VWAP,
- intraday trend score (-1..+1),
- volatility bucket.

The goal is to grow this into a data-driven model, but we start with a
transparent, tweakable formula for Block-E tuning.

IMPORTANT:
- This module is *not* wired into live gating yet.
- Use this for offline analysis / log-only EV fields first.
"""

from dataclasses import dataclass
from typing import Literal


VolBucket = Literal["low", "medium", "high"]


@dataclass
class OrbVwapFeatures:
    """
    ORB + VWAP features for a single trade context.

    orb_strength:   0.0 .. 1.0 (0 = weak ORB, 1 = very strong ORB breakout)
    above_vwap:     True if price is above VWAP at decision time.
    trend_score:    -1.0 .. +1.0 (downtrend .. uptrend)
    vol_bucket:     "low" | "medium" | "high" (realized/intraday vol regime)
    """

    orb_strength: float
    above_vwap: bool
    trend_score: float
    vol_bucket: VolBucket


def _vol_multiplier(vol_bucket: VolBucket) -> float:
    """
    Simple volatility adjustment factor.

    - low vol:    EV slightly compressed
    - medium vol: neutral
    - high vol:   EV slightly boosted if trend and ORB align, but risky

    This is just a starting point; we will re-fit these later.
    """
    if vol_bucket == "low":
        return 0.8
    if vol_bucket == "high":
        return 1.2
    return 1.0  # medium / default


def compute_orb_vwap_ev(
    symbol: str,
    regime: str,
    features: OrbVwapFeatures,
) -> float:
    """
    Compute a simple EV (in R units) from ORB + VWAP features.

    CURRENT FORMULA (starting point):
        base_ev = 0.10
        ev_orb  = 0.30 * orb_strength
        ev_vwap = +0.10 if above_vwap else -0.10
        ev_trend= 0.20 * trend_score
        vol_mul = _vol_multiplier(vol_bucket)

        raw_ev  = (base_ev + ev_orb + ev_vwap + ev_trend)
        ev      = raw_ev * vol_mul

    NOTES:
    - For a flat, neutral setup (orb_strength=0.0, above_vwap=True,
      trend_score=0.0, medium vol) -> EV ~ +0.20R.
    - For strong breakout above VWAP with strong uptrend and high vol,
      EV can approach +0.7R.
    - For weak/failed breakout below VWAP in downtrend, EV can go negative.

    We will later:
    - calibrate coefficients per symbol/regime,
    - drive orb_strength/trend/vol_bucket from real intraday stats,
    - and possibly clamp EV into configured EV bands.
    """

    f = features

    base_ev = 0.10   # base positive bias for vetted strategies
    ev_orb  = 0.30 * max(0.0, min(1.0, f.orb_strength))
    ev_vwap = 0.10 if f.above_vwap else -0.10
    ev_trend = 0.20 * max(-1.0, min(1.0, f.trend_score))

    vol_mul = _vol_multiplier(f.vol_bucket)

    raw_ev = base_ev + ev_orb + ev_vwap + ev_trend
    ev = raw_ev * vol_mul

    # For now, we do not clamp; we just return the computed EV.
    # Later we may clamp into EV bands (e.g. [-1.5R, +2.0R]) per symbol.
    return ev

def compute_effective_ev(
    ev_phase5: float | None,
    ev_model: float | None,
    *,
    pilot_weight: float = 0.25,
    max_abs_ev: float = 0.5,
) -> float:
    """
    Log-only helper: blend Phase-5 EV with ORB+VWAP model EV.

    - If ev_phase5 is None, treat it as 0.
    - If ev_model is None, fall back to ev_phase5.
    - Blend: effective = base + pilot_weight * (model - base)
      so pilot_weight=0.25 keeps the model as a soft suggestion.
    - Clamp to [-max_abs_ev, max_abs_ev].

    This is *not* used for live gating yet; it is only logged so we
    can study behaviour in Notion before wiring it into risk.
    """
    base = float(ev_phase5) if ev_phase5 is not None else 0.0
    if ev_model is None:
        model = base
    else:
        model = float(ev_model)

    blended = base + pilot_weight * (model - base)

    if blended > max_abs_ev:
        return max_abs_ev
    if blended < -max_abs_ev:
        return -max_abs_ev
    return blended