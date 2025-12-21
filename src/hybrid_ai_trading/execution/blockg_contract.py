# -*- coding: utf-8 -*-
from __future__ import annotations

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
            min_samples_ok_today=bool(d.get("min_samples_ok_today", False)),
        )


def load_blockg_status(path: Optional[str] = None) -> BlockGStatus:
    p = path or os.environ.get(_DEFAULT_ENV_KEY) or _DEFAULT_PATH
    with open(p, "r", encoding="utf-8") as f:
        d = json.load(f)
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
def ensure_symbol_blockg_ready(
    symbol: str,
    *,
    allow_paper: bool = True,
    is_paper: Optional[bool] = None,
    status_path: Optional[str] = None,
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
        env_flag = str(os.environ.get("HAT_IS_PAPER", "")).strip()
        is_paper = (env_flag != "0")

    if bool(is_paper) and bool(allow_paper):
        return

    st = load_blockg_status(status_path) if status_path else load_blockg_status()

    # Conservative: unknown symbols are not allowed for live
    if not symbol_ready(st, sym):
        raise RuntimeError(f"BLOCK-G: {sym} not ready (per-symbol flag false)")
