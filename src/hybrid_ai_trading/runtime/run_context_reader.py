from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from hybrid_ai_trading.runtime.run_context import RunContext


class RunContextNotFound(RuntimeError):
    pass


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_paths() -> list[Path]:
    root = _repo_root()
    return [
        root / "logs" / "run_context.json",
        root / "logs" / "runcontext_phase5_stub.json",  # legacy compat
    ]


def load_run_context(path: Optional[str] = None) -> RunContext:
    """
    Priority:
      1) explicit path
      2) env:HAT_RUN_CONTEXT_PATH
      3) repo/logs/run_context.json
      4) repo/logs/runcontext_phase5_stub.json (legacy)
    """
    if path:
        return _ctx_from_json(Path(path))

    p_env = os.environ.get("HAT_RUN_CONTEXT_PATH", "").strip()
    if p_env:
        pe = Path(p_env)
        if pe.exists():
            return _ctx_from_json(pe)

    for p in _default_paths():
        if p.exists():
            return _ctx_from_json(p)

    raise RunContextNotFound("RunContext JSON missing. Build via strict premarket.")


def _ctx_from_json(p: Path) -> RunContext:
    raw = p.read_text(encoding="utf-8-sig")
    obj = json.loads(raw)
    return _ctx_from_dict(obj)


def _ctx_from_dict(d: Dict[str, Any]) -> RunContext:
    symbol = str(d.get("symbol", "") or "NVDA")
    regime = str(d.get("regime", "") or "unknown")
    mode = str(d.get("mode", "") or "").strip().lower()
    if mode not in ("paper", "live", "backtest"):
        mode = "paper"

    as_of_date = str(d.get("as_of_date", "") or "").strip() or None

    is_paper = d.get("is_paper", None)
    if isinstance(is_paper, bool):
        return RunContext.from_env_and_args(
            symbol=symbol,
            regime=regime,
            mode=mode,
            is_paper=is_paper,
            as_of_date=as_of_date,
        )

    return RunContext.from_env_and_args(
        symbol=symbol,
        regime=regime,
        mode=mode,
        as_of_date=as_of_date,
    )

def get_ctx(
    symbol: str = "NVDA",
    meta: Any = None,
    mode_hint: Optional[str] = None,
    path: Optional[str] = None,
    allow_missing: bool = True,
) -> RunContext:
    """
    Unified RunContext acquisition (single source of truth).
    Priority:
      1) RunContext JSON via load_run_context (premarket-built)
      2) If missing and allow_missing=True: env-driven safe fallback (paper by default)

    - Never throws when allow_missing=True (fail-closed).
    - symbol/regime/mode may be hinted from meta for convenience.
    """
    # hints
    try:
        if isinstance(meta, dict):
            if not symbol:
                symbol = str(meta.get("symbol") or "NVDA")
            if mode_hint is None and meta.get("mode"):
                mode_hint = str(meta.get("mode"))
    except Exception:
        pass

    # 1) try load from JSON (strict premarket contract)
    try:
        ctx = load_run_context(path=path)
        # best-effort override symbol if caller asked (do NOT change mode/is_paper)
        try:
            if symbol and str(ctx.symbol).upper() != str(symbol).upper():
                return RunContext.from_env_and_args(
                    symbol=str(symbol),
                    regime=str(getattr(ctx, "regime", "unknown")),
                    mode=str(getattr(ctx, "mode", "paper")),
                    is_paper=bool(getattr(ctx, "is_paper", True)),
                    as_of_date=str(getattr(ctx, "as_of_date", "") or None),
                )
        except Exception:
            pass
        return ctx
    except Exception:
        if not allow_missing:
            raise

    # 2) fail-closed fallback
    try:
        regime = "unknown"
        if isinstance(meta, dict):
            regime = str(meta.get("regime", regime))
        return RunContext.from_env_and_args(
            symbol=str(symbol or "NVDA"),
            regime=str(regime),
            mode=(mode_hint if mode_hint else None),
        )
    except Exception:
        # ultimate fail-closed: paper
        return RunContext.from_env_and_args(symbol=str(symbol or "NVDA"), regime="unknown", mode="paper")
