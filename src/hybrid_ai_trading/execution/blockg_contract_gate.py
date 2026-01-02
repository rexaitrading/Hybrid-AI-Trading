from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hybrid_ai_trading.execution.blockg_enforce import BlockGNotReady, require_blockg_ready_for_live
from hybrid_ai_trading.execution.blockg_contract_reader import read_contract


def _is_live(ctx: Any = None) -> bool:
    # Canonical: ctx.mode wins, else env flag HAT_IS_PAPER=0 means live.
    try:
        if ctx is not None:
            mode = str(getattr(ctx, "mode", "")).strip().lower()
            if mode:
                return mode == "live"
    except Exception:
        pass
    return str(os.environ.get("HAT_IS_PAPER", "")).strip() == "0"


def _default_status_path(ctx: Any = None) -> Path:
    """
    Determine where blockg_status_stub.json is, without recomputing semantics.
    Priority:
      1) blockg_contract module resolver if present (ctx aware)
      2) env HAT_BLOCKG_STATUS_PATH
      3) repo-root/logs/blockg_status_stub.json (best-effort)
    """
    # 1) Prefer existing resolver (keeps ctx/json/env precedence centralized)
    try:
        from hybrid_ai_trading.execution import blockg_contract as _bc  # local import

        for name in ("default_blockg_status_path", "get_default_status_path", "resolve_status_path"):
            fn = getattr(_bc, name, None)
            if callable(fn):
                p = fn(ctx=ctx)
                if p:
                    return Path(p)
    except Exception:
        pass

    # 2) Env override
    envp = str(os.environ.get("HAT_BLOCKG_STATUS_PATH", "")).strip()
    if envp:
        return Path(envp)

    # 3) Best-effort repo-root/logs
    # This file is typically written by PS builders into logs/
    here = Path(__file__).resolve()
    repo = here.parents[3]  # .../src/hybrid_ai_trading/execution -> repo root
    return repo / "logs" / "blockg_status_stub.json"


def get_blockg_status(ctx: Any = None) -> Dict[str, Any]:
    p = _default_status_path(ctx=ctx)
    try:
        s = read_contract(p)
        return {
            "as_of_date": str(s.get("as_of_date","") or "").strip(),
            "nvda_blockg_ready": bool(s.get("nvda_blockg_ready", False)),
            "spy_blockg_ready": bool(s.get("spy_blockg_ready", False)),
            "qqq_blockg_ready": bool(s.get("qqq_blockg_ready", False)),
            "reasons_not_ready": list(s.get("reasons_not_ready", []) or []),
        }
    except Exception as e:
        return {
            "as_of_date": "",
            "nvda_blockg_ready": False,
            "spy_blockg_ready": False,
            "qqq_blockg_ready": False,
            "reasons_not_ready": [f"contract_load_failed:{type(e).__name__}"],
        }


def symbol_ready(symbol: str, ctx: Any = None, allow_paper: bool = True) -> Tuple[bool, List[str]]:
    sym = str(symbol).upper().strip()
    status = get_blockg_status(ctx=ctx)

    live = _is_live(ctx=ctx)
    if not live and allow_paper:
        return True, []

    # Use canonical enforcement logic (single source of truth)
    try:
        require_blockg_ready_for_live(sym, status=status)
        return True, []
    except BlockGNotReady as e:
        # keep reasons deterministic and list[str]
        return False, [str(x) for x in getattr(e, "reasons", [])] or [str(e)]
    except Exception as e:
        return False, [f"blockg_enforce_error:{type(e).__name__}:{e}"]


def require_symbol_ready(symbol: str, ctx: Any = None, allow_paper: bool = True) -> None:
    ok, reasons = symbol_ready(symbol, ctx=ctx, allow_paper=allow_paper)
    if not ok:
        raise BlockGNotReady(symbol=str(symbol).upper(), reasons=reasons)
