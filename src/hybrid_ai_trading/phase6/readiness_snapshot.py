from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from hybrid_ai_trading.execution.blockg_contract import read_blockg_status
from hybrid_ai_trading.portfolio.halts import evaluate_portfolio_halt


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def build_readiness_snapshot(
    *,
    portfolio_metrics: Dict[str, Any] | None = None,
    portfolio_cfg: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    st = read_blockg_status()
    pm = dict(portfolio_metrics or {})
    pcfg = dict(portfolio_cfg or {})

    # Portfolio halt decision (Notion-friendly)
    try:
        # Fail-closed: if halt is enabled, metrics must be present
        if bool(pcfg.get("enabled", False)) and (not isinstance(pm, dict) or len(pm) == 0):
            raise RuntimeError("portfolio_halt_metrics_missing")
        dec = evaluate_portfolio_halt(metrics=pm, cfg=pcfg)
        dec_obj = {"ok": bool(dec.ok), "reason": str(dec.reason), "details": (dec.details or None)}
    except Exception as e:
        msg = str(e)
        if "portfolio_halt_metrics_missing" in msg:
            dec_obj = {"ok": False, "reason": "portfolio_halt_metrics_missing", "details": None}
        else:
            dec_obj = {"ok": False, "reason": f"portfolio_halt_eval_error:{e}", "details": None}


    return {
        "blockg_status": dict(st),
        "portfolio_metrics": pm,
        "portfolio_halt": dec_obj,
        "portfolio_halt_cfg": pcfg,
    }
def write_readiness_snapshot(path: Path | None = None, *, portfolio_metrics: Dict[str, Any] | None = None, portfolio_cfg: Dict[str, Any] | None = None) -> Path:
    outp = path or (_repo_root() / "logs" / "phase6_readiness_snapshot.json")
    outp.parent.mkdir(parents=True, exist_ok=True)
    snap = build_readiness_snapshot(portfolio_metrics=portfolio_metrics, portfolio_cfg=portfolio_cfg)
    outp.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return outp
