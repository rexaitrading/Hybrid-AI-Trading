from __future__ import annotations

import json
import os

# --- Phase-7 preflight mode gate ---
# For optimizer daily (offline analytics), allow bypassing per-symbol Block-G readiness.
# Live/order paths must still enforce Block-G elsewhere (execution guards).
def _phase7_require_blockg() -> bool:
    v = os.getenv("HAT_PHASE7_REQUIRE_BLOCKG", "1").strip().lower()
    return v not in ("0","false","no","off")
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _summary_path() -> Path:
    envp = os.environ.get("HAT_PHASE6_DAILY_SUMMARY_PATH", "").strip()
    if envp:
        return Path(envp)
    return _repo_root() / "logs" / "phase6" / "phase6_daily_summary.json"


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        d = json.loads(path.read_text(encoding="utf-8-sig"))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def ensure_phase7_ready(*, required_symbols: Iterable[str] = ("NVDA",), as_of_date: str | None = None) -> Dict[str, Any]:
    """
    Phase-7 preflight gate (fail-closed):
    - Requires Phase-6 daily summary exists and is readable
    - Requires readiness.blockg.<symbol>_blockg_ready True for required symbols (when known)
    - Requires readiness.portfolio_halt.ok True
    - Requires gatescore_by_symbol contains required symbols
    """
    enable_spyqqq = (os.environ.get("HAT_BLOCKG_ENABLE_SPYQQQ","") == "1")
    enable_spyonly = (os.environ.get("HAT_BLOCKG_ENABLE_SPYONLY","") == "1")
    p = _summary_path()
    if not p.exists():
        raise RuntimeError(f"PHASE7_PREFLIGHT_DENY: missing_phase6_daily_summary path={p}")

    d = _read_json(p)
    if not d:
        raise RuntimeError(f"PHASE7_PREFLIGHT_DENY: unreadable_phase6_daily_summary path={p}")

    if as_of_date is not None:
        got = str(d.get("as_of_date", "") or "").strip()
        if got != str(as_of_date).strip():
            raise RuntimeError(f"PHASE7_PREFLIGHT_DENY: as_of_date_mismatch want={as_of_date} got={got}")

    readiness = d.get("readiness", {}) if isinstance(d.get("readiness", {}), dict) else {}
    blockg = readiness.get("blockg", {}) if isinstance(readiness.get("blockg", {}), dict) else {}
    ph = readiness.get("portfolio_halt", {}) if isinstance(readiness.get("portfolio_halt", {}), dict) else {}

    if not bool(ph.get("ok", False)):
        raise RuntimeError(f"PHASE7_PREFLIGHT_DENY: portfolio_halt_not_ok reason={ph.get('reason','')}")

    gs = d.get("gatescore_by_symbol", {}) if isinstance(d.get("gatescore_by_symbol", {}), dict) else {}
    req_syms = [str(s).strip().upper() for s in required_symbols if str(s).strip()]

    # gatescore must cover symbols
    missing = [s for s in req_syms if s not in gs]
    if missing:
        raise RuntimeError(f"PHASE7_PREFLIGHT_DENY: gatescore_missing_symbols missing={missing}")

    if _phase7_require_blockg():
        # blockg checks for known symbols (strict for NVDA; optional for SPY/QQQ if asked)
        for s in req_syms:
            if s == "NVDA":
                if not bool(blockg.get("nvda_blockg_ready", False)):
                    raise RuntimeError("PHASE7_PREFLIGHT_DENY: blockg_nvda_not_ready")
            elif s == "SPY" and (enable_spyqqq or enable_spyonly):
                if "spy_blockg_ready" in blockg and not bool(blockg.get("spy_blockg_ready", False)):
                    raise RuntimeError("PHASE7_PREFLIGHT_DENY: blockg_spy_not_ready")
            elif s == "QQQ" and enable_spyqqq:
                if "qqq_blockg_ready" in blockg and not bool(blockg.get("qqq_blockg_ready", False)):
                    raise RuntimeError("PHASE7_PREFLIGHT_DENY: blockg_qqq_not_ready")
    

    return d
