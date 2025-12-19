"""
PaperLiveWithoutIBG NVDA Phase-5 runner.

- NO broker / NO IBG; pure in-process paper runner.
- Reads NVDA candidate trades from logs/paper_trades.jsonl.
- For each NVDA row, calls Phase-5 guarded placement (paper-safe: engine.is_paper=True):
  - Phase-5 EV-band surface (ev_mu/ev_band_abs),
  - RiskManager Phase-5 gates (daily loss cap, no-averaging, etc.)
- Writes results to logs/nvda_phase5_paperlive_results.jsonl
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hybrid_ai_trading.execution.execution_engine_phase5_guard import (
    place_order_phase5_with_guard,
)
from hybrid_ai_trading.risk.risk_phase5_ev_bands import get_ev_and_band
from hybrid_ai_trading.risk.risk_manager import RiskManager


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class PaperEngine:
    """
    Minimal in-process engine for paper trading without IBG.

    - Maintains positions dict {symbol: qty}
    - Exposes .risk_manager to reuse Phase-5 risk gates
    - place_order() updates positions and returns a simple dict
    """

    def __init__(self) -> None:
        self.is_paper = True
        self.positions: Dict[str, float] = {}

        self.risk_manager = RiskManager()
        if hasattr(self.risk_manager, "positions"):
            setattr(self.risk_manager, "positions", self.positions)

        # Ensure a conservative paper cap exists if RiskManager config is missing the field
        import types

        cfg = getattr(self.risk_manager, "config", None)
        if cfg is None:
            self.risk_manager.config = types.SimpleNamespace(phase5_daily_loss_cap=-500.0)
        elif not hasattr(cfg, "phase5_daily_loss_cap"):
            cfg.phase5_daily_loss_cap = -500.0

    def place_order(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        symbol = str(kwargs.get("symbol") or kwargs.get("sym") or "NVDA").upper()
        side = str(kwargs.get("side") or "").upper()
        qty = kwargs.get("qty") or 0.0

        try:
            qty_f = float(qty)
        except (TypeError, ValueError):
            qty_f = 0.0

        pos = float(self.positions.get(symbol, 0.0))
        if side == "BUY":
            pos += qty_f
        elif side == "SELL":
            pos -= qty_f

        self.positions[symbol] = pos

        return {
            "status": "ok",
            "engine_called": True,
            "symbol": symbol,
            "side": side,
            "qty": qty_f,
            "new_position": pos,
        }


def load_nvda_paper_trades() -> List[Dict[str, Any]]:
    """Load NVDA rows from logs/paper_trades.jsonl and sort by ts ascending."""
    src = Path("logs") / "paper_trades.jsonl"
    if not src.exists():
        print(f"{src} not found")
        return []

    rows: List[Dict[str, Any]] = []
    with src.open("r", encoding="utf-8-sig") as f:
        for line in f:
            ln = line.strip()
            if not ln:
                continue
            try:
                row = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if str(row.get("symbol", "")).upper() != "NVDA":
                continue
            ts = row.get("ts")
            if not ts:
                continue
            rows.append(row)

    rows.sort(key=lambda r: str(r.get("ts")))
    return rows


def infer_side_and_qty(row: Dict[str, Any]) -> Dict[str, Any]:
    """Infer side/qty from a paper_trades row (safe defaults)."""
    signal = str(row.get("signal") or "").upper()
    if signal.startswith("LONG"):
        side = "BUY"
    elif signal.startswith("SHORT"):
        side = "SELL"
    else:
        side = "BUY"

    qty = row.get("qty", 1.0)
    return {"side": side, "qty": qty}


def _ensure_ev_band(out: Dict[str, Any]) -> None:
    """Fail-closed safe EV-band surface: ensure ev_mu/ev_band_abs exist when possible."""
    try:
        if out.get("ev_mu") is None or out.get("ev_band_abs") is None:
            ev_mu, ev_band_abs = get_ev_and_band(str(out.get("regime") or "NVDA_BPLUS_LIVE"))
            out.setdefault("ev_mu", ev_mu)
            out.setdefault("ev_band_abs", ev_band_abs)
            p5 = out.get("phase5_result") or {}
            if isinstance(p5, dict):
                p5.setdefault("ev_mu", out.get("ev_mu"))
                p5.setdefault("ev_band_abs", out.get("ev_band_abs"))
                p5.setdefault("source", "ev_band_table")
                out["phase5_result"] = p5
    except Exception:
        return


def main() -> int:
    out_path = Path("logs") / "nvda_phase5_paperlive_results.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    engine = PaperEngine()
    trades = load_nvda_paper_trades()
    print(f"Loaded {len(trades)} NVDA paper trade candidates.")

    with out_path.open("w", encoding="utf-8") as out_f:
        for idx, row in enumerate(trades, start=1):
            ts = row.get("ts")
            info = infer_side_and_qty(row)
            side = info["side"]
            qty = info["qty"]

            # Paper-safe guarded placement (engine.is_paper=True bypasses Block-G)
            result = place_order_phase5_with_guard(
                engine,
                symbol="NVDA",
                entry_ts=ts,
                side=side,
                qty=qty,
                price=row.get("price"),
                regime="NVDA_BPLUS_LIVE",
            )

            out: Dict[str, Any] = dict(result)
            out["idx"] = idx
            out["ts_trade"] = ts
            out.setdefault("entry_ts", out.get("ts_trade"))
            out["ts_utc"] = now_utc_iso()
            out["position_after"] = engine.positions.get("NVDA", 0.0)

            # Optional GateScore fields copied from signal row if present
            if "edge_ratio" in row:
                out["edge_ratio"] = row.get("edge_ratio")
            if "micro_score" in row:
                out["micro_score"] = row.get("micro_score")

            _ensure_ev_band(out)

            out_f.write(json.dumps(out, ensure_ascii=False) + "\n")

    print(f"Wrote NVDA Phase-5 paper-live results to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())