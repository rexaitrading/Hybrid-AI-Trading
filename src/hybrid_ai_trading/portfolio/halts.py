from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


class PortfolioHalt(RuntimeError):
    """Raised when portfolio-level risk halts block trading (fail-closed)."""


@dataclass
class PortfolioHaltStatus:
    ok: bool
    reason: str = ""
    details: Optional[Dict[str, Any]] = None


def evaluate_portfolio_halt(*, metrics: Dict[str, Any], cfg: Dict[str, Any]) -> PortfolioHaltStatus:
    """
    cfg keys:
      enabled: bool (default False)
      max_var95: float
      max_cvar95: float
      max_drawdown: float
    """
    if not bool(cfg.get("enabled", False)):
        return PortfolioHaltStatus(ok=True, reason="portfolio_halt_disabled")

    var95 = float(metrics.get("var95", 0.0) or 0.0)
    cvar95 = float(metrics.get("cvar95", 0.0) or 0.0)
    dd = float(metrics.get("drawdown", 0.0) or 0.0)

    mv = cfg.get("max_var95", None)
    if mv is not None and var95 > float(mv):
        return PortfolioHaltStatus(ok=False, reason="var95_exceeded", details={"var95": var95, "max_var95": float(mv)})

    mc = cfg.get("max_cvar95", None)
    if mc is not None and cvar95 > float(mc):
        return PortfolioHaltStatus(ok=False, reason="cvar95_exceeded", details={"cvar95": cvar95, "max_cvar95": float(mc)})

    mdd = cfg.get("max_drawdown", None)
    if mdd is not None and dd > float(mdd):
        return PortfolioHaltStatus(ok=False, reason="drawdown_exceeded", details={"drawdown": dd, "max_drawdown": float(mdd)})

    return PortfolioHaltStatus(ok=True, reason="portfolio_halt_ok")


def require_portfolio_halt_ok(*, metrics: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    st = evaluate_portfolio_halt(metrics=metrics, cfg=cfg)
    if not st.ok:
        raise PortfolioHalt(f"PORTFOLIO_HALT: {st.reason} details={st.details}")
