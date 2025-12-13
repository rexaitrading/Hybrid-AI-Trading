from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class RiskEnvelope:
    """
    Explicitly-armed risk budget envelope ("Special-Mode").

    Armed iff:
      - env HAT_SPECIAL_MODE == "1"
      - logs/risk_envelope.json exists, is valid JSON, and as_of_date == today and armed == true
    """
    as_of_date: str
    armed: bool
    name: str = "special"
    reason: str = ""
    expires_utc: Optional[str] = None

    # caps (optional overrides)
    max_leverage: Optional[float] = None
    max_portfolio_exposure: Optional[float] = None
    per_trade_notional_cap: Optional[float] = None

    # future wiring (not enforced in OrderManager yet)
    size_multiplier: Optional[float] = None
    max_trades_per_day: Optional[int] = None
    day_loss_cap_pct: Optional[float] = None


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _is_env_armed() -> bool:
    return (os.getenv("HAT_SPECIAL_MODE", "") or "").strip() == "1"


def load_risk_envelope(repo_root: Path = Path(".")) -> Optional[RiskEnvelope]:
    """
    Load envelope from logs/risk_envelope.json if present and valid.
    Returns None on any parse/validation error (fail-safe).
    """
    try:
        p = (repo_root / "logs" / "risk_envelope.json")
        if not p.exists():
            return None
        raw = p.read_text(encoding="utf-8")
        j = json.loads(raw)

        as_of = str(j.get("as_of_date", "")).strip()
        armed = bool(j.get("armed", False))

        env = RiskEnvelope(
            as_of_date=as_of,
            armed=armed,
            name=str(j.get("name", "special") or "special"),
            reason=str(j.get("reason", "") or ""),
            expires_utc=(str(j.get("expires_utc")) if j.get("expires_utc") is not None else None),
            max_leverage=_to_f(j.get("max_leverage")),
            max_portfolio_exposure=_to_f(j.get("max_portfolio_exposure")),
            per_trade_notional_cap=_to_f(j.get("per_trade_notional_cap")),
            size_multiplier=_to_f(j.get("size_multiplier")),
            max_trades_per_day=_to_i(j.get("max_trades_per_day")),
            day_loss_cap_pct=_to_f(j.get("day_loss_cap_pct")),
        )
        return env
    except Exception:
        return None


def is_special_mode_armed(repo_root: Path = Path(".")) -> bool:
    """
    Strict arming rule: require BOTH env + today's file.
    """
    if not _is_env_armed():
        return False

    env = load_risk_envelope(repo_root=repo_root)
    if env is None:
        return False

    if not env.armed:
        return False

    # today-ness check (UTC date)
    return env.as_of_date == _today_utc()


def effective_caps(repo_root: Path, equity: Optional[float] = None) -> dict:
    """
    Return dict of cap overrides if Special-Mode is armed; else {}.
    Includes hard ceilings to prevent insane inputs.
    """
    if not is_special_mode_armed(repo_root=repo_root):
        return {}

    env = load_risk_envelope(repo_root=repo_root)
    if env is None:
        return {}

    # Hard ceilings (institutional safety)
    hard_max_leverage = 3.0
    hard_max_exposure = 0.75

    out = {}

    if env.max_leverage is not None:
        out["max_leverage"] = float(min(env.max_leverage, hard_max_leverage))

    if env.max_portfolio_exposure is not None:
        out["max_portfolio_exposure"] = float(min(env.max_portfolio_exposure, hard_max_exposure))

    if env.per_trade_notional_cap is not None:
        cap = float(env.per_trade_notional_cap)
        # Optional equity-relative sanity if equity supplied
        if equity is not None and equity > 0:
            cap = min(cap, float(equity) * 0.50)  # never > 50% equity in one trade via envelope
        out["per_trade_notional_cap"] = cap

    return out


def _to_f(x) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _to_i(x) -> Optional[int]:
    try:
        if x is None:
            return None
        return int(x)
    except Exception:
        return None
