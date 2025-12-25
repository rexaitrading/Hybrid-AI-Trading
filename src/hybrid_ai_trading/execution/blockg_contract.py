# -*- coding: utf-8 -*-
from __future__ import annotations
from hybrid_ai_trading.execution.blockg_errors import BlockGNotReady
from hybrid_ai_trading.runtime.run_context_reader import load_run_context
from hybrid_ai_trading.runtime.run_context import RunContext

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

_DEFAULT_ENV_KEY = "HAT_BLOCKG_STATUS_PATH"
_DEFAULT_PATH = os.path.join("logs", "blockg_status_stub.json")


@dataclass(frozen=True)
class BlockGStatus:
    as_of_date: str
    nvda_blockg_ready: bool = False
    spy_blockg_ready: bool = False
    qqq_blockg_ready: bool = False

    # freshness/quality fields (contract-driven)
    phase4_ok_today: bool = False
    ev_hard_daily_ok_today: bool = False
    gatescore_fresh_today: bool = False
    gatescore_fresh_for_session: bool = False
    gatescore_recent_enough: bool = False
    gatescore_age_days: int = 0
    min_samples_ok_today: bool = False

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "BlockGStatus":
        return BlockGStatus(
            as_of_date=str(d.get("as_of_date") or ""),
            nvda_blockg_ready=bool(d.get("nvda_blockg_ready", False)),
            spy_blockg_ready=bool(d.get("spy_blockg_ready", False)),
            qqq_blockg_ready=bool(d.get("qqq_blockg_ready", False)),
            phase4_ok_today=bool(d.get("phase4_ok_today", False)),
            ev_hard_daily_ok_today=bool(d.get("ev_hard_daily_ok_today", False)),
            gatescore_fresh_today=bool(d.get("gatescore_fresh_today", False)),
            gatescore_fresh_for_session=bool(d.get("gatescore_fresh_for_session", False)),
            gatescore_recent_enough=bool(d.get("gatescore_recent_enough", False)),
            gatescore_age_days=int(d.get("gatescore_age_days", 0) or 0),
            min_samples_ok_today=bool(d.get("min_samples_ok_today", False)),
        )


def load_blockg_status(path: Optional[str] = None) -> BlockGStatus:
    p = path or os.environ.get(_DEFAULT_ENV_KEY) or _DEFAULT_PATH
    try:

        with open(p, "r", encoding="utf-8") as f:

            d = json.load(f)

    except FileNotFoundError:

        # Fail-closed: missing contract is NOT a system error; it is "NOT READY"

        raise BlockGNotReady(f"Block-G status missing at: {p}")
    return BlockGStatus.from_dict(d)


def symbol_ready(st: BlockGStatus, symbol: str) -> bool:
    s = (symbol or "").upper().strip()
    if s == "NVDA":
        return st.nvda_blockg_ready
    if s == "SPY":
        return st.spy_blockg_ready
    if s == "QQQ":
        return st.qqq_blockg_ready
    return False
# ---------------------------------------------------------------------------
# Backward-compatible contract gate (tests + legacy call sites expect this name)
# ---------------------------------------------------------------------------
def _resolve_is_paper_from_ctx(ctx: RunContext | None = None) -> bool:
    """
    Canonical is_paper resolver:
      1) ctx.is_paper
      2) logs/run_context.json via load_run_context()
      3) env:HAT_IS_PAPER
    Default is paper-safe.
    """
    try:
        if ctx is not None:
            # Unified mode semantics: ctx.mode='live' implies LIVE (is_paper=False)
            try:
                if str(getattr(ctx, "mode", "")).lower() == "live":
                    return False
            except Exception:
                pass

            return bool(getattr(ctx, "is_paper", True))
    except Exception:
        return False  # fail-closed -> LIVE -> contract blocks

    try:
        rc = load_run_context()
        return bool(getattr(rc, "is_paper", True))
    except Exception:
        pass

    try:
        return os.environ.get("HAT_IS_PAPER", "1").strip() != "0"
    except Exception:
        return True

def ensure_symbol_blockg_ready(symbol: str,
    *,
    allow_paper: bool = True,
    is_paper: Optional[bool] = None,
    status_path: Optional[str] = None,
    ctx: RunContext | None = None,
) -> None:
    """
    Fail-closed contract gate.

    - If allow_paper=True and is_paper=True -> bypass (paper-safe path).
    - Otherwise requires per-symbol ready flag in Block-G status JSON.

    This function is intentionally lightweight and stable because many tests
    monkeypatch it directly.
    """
    sym = str(symbol or "").upper().strip()

    # Determine paper/live intent (fail-safe default: paper)
    if is_paper is None:
        is_paper = _resolve_is_paper_from_ctx(ctx)
    if bool(is_paper) and bool(allow_paper):
        return

    st = load_blockg_status(status_path) if status_path else load_blockg_status()
    # Per-symbol readiness (fail-closed for LIVE)
    mode = getattr(ctx, "mode", None) if ctx is not None else None
    env_live = (str(os.environ.get("HAT_IS_PAPER", "1")).strip() == "0")
    live = (is_paper is False) or (str(mode).lower() == "live") or env_live
    if live:
        sym_u = str(symbol).upper().strip()
        key = f"{sym_u.lower()}_blockg_ready"
        flag = getattr(st, key, None)
        if flag is None:
            # Fail-closed if field missing
            raise BlockGNotReady(f"Block-G not ready: {key}=missing")
        if flag is not True:
            raise BlockGNotReady(f"Block-G not ready: {key}={flag}")


    # -----------------------------------------------------------------------
    # Upgrade #2: freshness/quality checks (contract-only, no recomputation)
    # LIVE path must satisfy these daily requirements before per-symbol gating.
    # -----------------------------------------------------------------------
    if not bool(getattr(st, "phase4_ok_today", False)):
        raise BlockGNotReady("BLOCK-G: phase4_ok_today false")
    if not bool(getattr(st, "ev_hard_daily_ok_today", False)):
        raise BlockGNotReady("BLOCK-G: ev_hard_daily_ok_today false")
    if hasattr(st, "phase23_health_ok_today") and (not bool(getattr(st, "phase23_health_ok_today", False))):
        raise BlockGNotReady("BLOCK-G: phase23_health_ok_today false")

    if not bool(getattr(st, "gatescore_fresh_for_session", False)):
        raise BlockGNotReady("BLOCK-G: gatescore_fresh_for_session false")
    if not bool(getattr(st, "gatescore_recent_enough", False)):
        raise BlockGNotReady("BLOCK-G: gatescore_recent_enough false")
    # Defense-in-depth: if age field is present, enforce max=3 days
    try:
        age = int(getattr(st, "gatescore_age_days", 0))
        if age > 3:
            raise BlockGNotReady(f"BLOCK-G: gatescore_age_days too old ({age} > 3)")
    except Exception:
        if hasattr(st, "gatescore_age_days"):
            raise BlockGNotReady("BLOCK-G: gatescore_age_days invalid")
    if hasattr(st, "gatescore_samples_ok") and (not bool(getattr(st, "gatescore_samples_ok", False))):
        raise BlockGNotReady("BLOCK-G: gatescore_samples_ok false")
    if hasattr(st, "gatescore_threshold_ok_today") and (not bool(getattr(st, "gatescore_threshold_ok_today", False))):
        raise BlockGNotReady("BLOCK-G: gatescore_threshold_ok_today false")

    # Conservative: unknown symbols are not allowed for live
    if not symbol_ready(st, sym):
        raise BlockGNotReady(f"BLOCK-G: {sym} not ready (per-symbol flag false)")
