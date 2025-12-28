from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_equity_curve_csv(path: Path) -> List[Tuple[float, float]]:
    """
    Best-effort read of an equity curve CSV:
      columns may include: ts,equity  OR  datetime,equity  OR similar.
    Returns list of (t, equity) with t as float index when timestamp parse is unknown.
    """
    raw = path.read_text(encoding="utf-8-sig").splitlines()
    if len(raw) < 2:
        return []
    header = [h.strip().lower() for h in raw[0].split(",")]
    try:
        i_eq = header.index("equity")
    except Exception:
        return []
    out: List[Tuple[float, float]] = []
    for i, ln in enumerate(raw[1:], start=1):
        cols = ln.split(",")
        if len(cols) <= i_eq:
            continue
        try:
            eq = float(str(cols[i_eq]).strip().strip('"') or "0")
        except Exception:
            continue
        out.append((float(i), float(eq)))
    return out


def build_portfolio_metrics_snapshot() -> Dict[str, Any]:
    """
    Produce portfolio metrics for Phase-6 halt checks.
    Primary source (today): equity curve CSV if present.
    Fallback: PortfolioTracker default state (returns zeros) — used only when curve is absent,
             and ops may still fail-closed if cfg.enabled is True.
    """
    repo = _repo_root()
    curve_csv = repo / "logs" / "portfolio_equity_curve.csv"

    tracker = PortfolioTracker(starting_equity=100000.0)

    curve = []
    if curve_csv.exists():
        curve = _read_equity_curve_csv(curve_csv)
        for _, eq in curve:
            # append equity history points
            tracker.history.append((tracker.history[-1][0], float(eq)))
        if curve:
            tracker.equity = float(curve[-1][1])

    rep = tracker.report()
    # Keep only the keys Phase-6 halt cares about (plus equity for reference)
    out = {
        "equity": float(rep.get("equity", 0.0) or 0.0),
        "drawdown": float(rep.get("drawdown", 0.0) or 0.0),
        "var95": float(rep.get("var95", 0.0) or 0.0),
        "cvar95": float(rep.get("cvar95", 0.0) or 0.0),
        "source": ("portfolio_equity_curve.csv" if curve_csv.exists() else "portfolio_tracker_default"),
    }
    return out


def write_portfolio_metrics_snapshot(path: Path | None = None) -> Path:
    repo = _repo_root()
    outp = path or (repo / "logs" / "phase6_portfolio_metrics.json")
    outp.parent.mkdir(parents=True, exist_ok=True)
    snap = build_portfolio_metrics_snapshot()
    outp.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return outp
