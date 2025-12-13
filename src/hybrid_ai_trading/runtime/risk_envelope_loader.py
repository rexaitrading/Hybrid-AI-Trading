from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple


@dataclass(frozen=True)
class RiskEnvelope:
    """
    Explicitly-armed risk budget envelope ("Special-Mode").
    OFF by default; ON only with explicit operator arm + today's contract file.

    Armed iff:
      - env HAT_SPECIAL_MODE == "1"
      - logs/risk_envelope.json exists, is valid JSON, armed == true, as_of_date == today's UTC date
      - expires_utc (if set) has NOT passed
    """
    as_of_date: str
    armed: bool
    name: str = "special"
    reason: str = ""
    ts_utc: Optional[str] = None
    expires_utc: Optional[str] = None

    # caps (optional overrides)
    max_leverage: Optional[float] = None
    max_portfolio_exposure: Optional[float] = None
    per_trade_notional_cap: Optional[float] = None

    # sizing/throttles
    size_multiplier: Optional[float] = None

    # auto-dearm tripwire (fraction drawdown from peak)
    max_drawdown_pct: Optional[float] = None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _today_utc() -> str:
    return _now_utc().date().isoformat()


def _is_env_armed() -> bool:
    return (os.getenv("HAT_SPECIAL_MODE", "") or "").strip() == "1"


def _to_f(x) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _parse_iso_utc(s: str) -> Optional[datetime]:
    try:
        # allow trailing Z
        t = (s or "").strip()
        if not t:
            return None
        if t.endswith("Z"):
            t = t[:-1] + "+00:00"
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def load_risk_envelope(repo_root: Path = Path(".")) -> Optional[RiskEnvelope]:
    """
    Load envelope from logs/risk_envelope.json if present and valid JSON.
    Returns None on parse error (fail-safe).
    """
    try:
        p = repo_root / "logs" / "risk_envelope.json"
        if not p.exists():
            return None
        j = json.loads(p.read_text(encoding="utf-8"))
        return RiskEnvelope(
            ts_utc=str(j.get("ts_utc") or "") or None,
            as_of_date=str(j.get("as_of_date") or "").strip(),
            armed=bool(j.get("armed", False)),
            name=str(j.get("name") or "special"),
            reason=str(j.get("reason") or ""),
            expires_utc=(str(j.get("expires_utc")) if j.get("expires_utc") is not None else None),
            max_leverage=_to_f(j.get("max_leverage")),
            max_portfolio_exposure=_to_f(j.get("max_portfolio_exposure")),
            per_trade_notional_cap=_to_f(j.get("per_trade_notional_cap")),
            size_multiplier=_to_f(j.get("size_multiplier")),
            max_drawdown_pct=_to_f(j.get("max_drawdown_pct")),
        )
    except Exception:
        return None


def _expires_ok(expires_utc: Optional[str]) -> bool:
    if not expires_utc:
        return True
    dt = _parse_iso_utc(expires_utc)
    if dt is None:
        # invalid timestamp -> fail-safe: treat as NOT ok (forces dearm)
        return False
    return _now_utc() <= dt


def is_special_mode_armed(repo_root: Path = Path(".")) -> bool:
    """
    Strict arming rule: require BOTH env + today's file + not expired.
    """
    if not _is_env_armed():
        return False

    env = load_risk_envelope(repo_root=repo_root)
    if env is None or (not env.armed):
        return False

    if env.as_of_date != _today_utc():
        return False

    if not _expires_ok(env.expires_utc):
        return False

    return True


def effective_size_multiplier(repo_root: Path = Path(".")) -> float:
    """
    Returns 1.0 unless Special-Mode is armed. Hard-capped to avoid runaway sizing.
    """
    if not is_special_mode_armed(repo_root=repo_root):
        return 1.0

    env = load_risk_envelope(repo_root=repo_root)
    if env is None:
        return 1.0

    m = env.size_multiplier if env.size_multiplier is not None else 1.0

    # Hard safety envelope: min 0.25x, max 2.0x
    try:
        m = float(m)
    except Exception:
        return 1.0

    if m < 0.25:
        m = 0.25
    if m > 2.0:
        m = 2.0
    return m



def effective_caps(repo_root: Path, equity: Optional[float] = None) -> dict:
    """
    Return dict of cap overrides if Special-Mode is armed; else {}.

    This is the ONLY function OrderManager needs for envelope caps.
    Must be:
      - explicitly armed (HAT_SPECIAL_MODE=1)
      - today's UTC contract
      - not expired
    """
    if not is_special_mode_armed(repo_root=repo_root):
        return {}

    env = load_risk_envelope(repo_root=repo_root)
    if env is None:
        return {}

    # Institutional hard ceilings (never allow runaway)
    hard_max_leverage = 3.0
    hard_max_exposure = 0.75

    out: dict = {}

    if env.max_leverage is not None:
        try:
            out["max_leverage"] = float(min(float(env.max_leverage), hard_max_leverage))
        except Exception:
            pass

    if env.max_portfolio_exposure is not None:
        try:
            out["max_portfolio_exposure"] = float(min(float(env.max_portfolio_exposure), hard_max_exposure))
        except Exception:
            pass

    if env.per_trade_notional_cap is not None:
        try:
            cap = float(env.per_trade_notional_cap)
            # Optional equity-relative sanity if equity supplied
            if equity is not None:
                eq = float(equity)
                if eq > 0:
                    cap = min(cap, eq * 0.50)  # never > 50% equity in one trade via envelope
            out["per_trade_notional_cap"] = cap
        except Exception:
            pass

    return out

def _write_disarm(repo_root: Path, reason: str) -> None:
    """
    Best-effort write-back to logs/risk_envelope.json marking armed=false (UTF-8 no BOM).
    Must never raise.
    """
    try:
        p = repo_root / "logs" / "risk_envelope.json"
        if not p.exists():
            return
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            j = {}
        j["ts_utc"] = _now_utc().isoformat()
        j["as_of_date"] = _today_utc()
        j["armed"] = False
        j["reason"] = str(reason or "auto_disarm")
        # keep expires_utc as-is (audit trail)
        raw = json.dumps(j, indent=4)
        p.write_bytes(raw.encode("utf-8"))
    except Exception:
        return


def check_and_auto_disarm(repo_root: Path, equity: Optional[float], equity_peak: Optional[float]) -> Tuple[bool, str]:
    """
    Returns (disarmed, reason). Never raises.

    Triggers:
      - expiry passed (expires_utc)
      - drawdown breach vs env.max_drawdown_pct (if set and peak>0)
    """
    try:
        if not _is_env_armed():
            return (False, "")

        env = load_risk_envelope(repo_root=repo_root)
        if env is None or (not env.armed):
            return (False, "")

        # Expiry tripwire
        if not _expires_ok(env.expires_utc):
            _write_disarm(repo_root, "auto_disarm:expired")
            return (True, "expired")

        # Drawdown tripwire
        dd = None
        if env.max_drawdown_pct is not None and equity is not None and equity_peak is not None:
            try:
                peak = float(equity_peak)
                cur = float(equity)
                if peak > 0:
                    dd = max(0.0, (peak - cur) / peak)
            except Exception:
                dd = None

        if dd is not None and env.max_drawdown_pct is not None:
            try:
                thr = float(env.max_drawdown_pct)
                if thr > 0 and dd >= thr:
                    _write_disarm(repo_root, f"auto_disarm:drawdown_breach dd={dd:.4f} thr={thr:.4f}")
                    return (True, "drawdown_breach")
            except Exception:
                pass

        return (False, "")
    except Exception:
        return (False, "")
