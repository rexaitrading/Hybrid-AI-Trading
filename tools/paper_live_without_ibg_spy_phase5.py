"""
PaperLiveWithoutIBG SPY Phase-5 runner.

- NO broker / NO IBG; this is a pure in-process paper runner.
- Reads SPY candidate trades from logs/paper_trades.jsonl.
- For each SPY row, calls place_order_phase5(engine, ...) to apply:
  - Phase-5 decisions gate (from spy_phase5_decisions.json),
  - RiskManager.phase5_no_averaging_down_for_symbol (if implemented).
- Logs decisions/results to logs/spy_phase5_paperlive_results.jsonl.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from hybrid_ai_trading.execution.execution_engine_phase5_guard import (
    place_order_phase5_with_guard as place_order_phase5,
)
from hybrid_ai_trading.risk.risk_manager import RiskManager


class PaperEngine:
    """
    Minimal in-process engine for paper trading without IBG (SPY).

    - Maintains a simple positions dict {symbol: qty}.
    - Exposes .risk_manager so place_order_phase5 can invoke the
      phase5_no_averaging_down_for_symbol hook.
    - place_order() updates positions and returns a simple dict.
    """

    def __init__(self) -> None:
        self.positions: Dict[str, float] = {}
        self._logger = None  # you can swap in a real logger later

        # Wrap real RiskManager so we can reuse its no-averaging logic.
        self.risk_manager = RiskManager()
        # If RiskManager uses .positions, hook it up:
        setattr(self.risk_manager, "positions", self.positions)
        # Configure Phase-5 daily loss cap for paper runs (per docs/SPY_ORB_Phase5_Config.md).
        import types
        cfg = getattr(self.risk_manager, "config", None)
        if cfg is None:
            self.risk_manager.config = types.SimpleNamespace(phase5_daily_loss_cap=-500.0)
        elif not hasattr(cfg, "phase5_daily_loss_cap"):
            cfg.phase5_daily_loss_cap = -500.0

    def get_position_for_symbol(self, symbol: str) -> float:
        return float(self.positions.get(symbol, 0.0))

    def place_order(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Simulate an order fill in paper mode.

        Expected kwargs at least:
            symbol, side, qty
        """
        symbol = str(kwargs.get("symbol") or kwargs.get("sym") or "SPY")
        side = str(kwargs.get("side") or "").upper()
        qty = kwargs.get("qty") or 0.0

        try:
            qty_f = float(qty)
        except (TypeError, ValueError):
            qty_f = 0.0

        pos = self.positions.get(symbol, 0.0)
        if side == "BUY":
            pos += qty_f
        elif side == "SELL":
            pos -= qty_f
        # else: unknown side -> no position update

        self.positions[symbol] = pos

        return {
            "status": "ok",
            "engine_called": True,
            "symbol": symbol,
            "side": side,
            "qty": qty_f,
            "new_position": pos,
        }


def load_spy_paper_trades() -> List[Dict[str, Any]]:
    """
    Load SPY rows from logs/paper_trades.jsonl and sort by ts ascending.
    """
    src = Path("logs") / "paper_trades.jsonl"
    if not src.exists():
        raise SystemExit(f"{src} not found")

    rows: List[Dict[str, Any]] = []
    with src.open("r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(row.get("symbol", "")).upper() != "SPY":
                continue
            ts = row.get("ts")
            if not ts:
                continue
            rows.append(row)

    rows.sort(key=lambda r: str(r.get("ts")))
    return rows


def infer_side_and_qty(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Infer side and qty from a paper_trades row.

    Heuristic:
    - If row['signal'] starts with 'LONG' -> BUY
    - If row['signal'] starts with 'SHORT' -> SELL
    - Else default BUY.

    - qty: row['qty'] if present, else 1.0
    """
    signal = str(row.get("signal") or "").upper()
    if signal.startswith("LONG"):
        side = "BUY"
    elif signal.startswith("SHORT"):
        side = "SELL"
    else:
        side = "BUY"

    qty = row.get("qty", 1.0)

    return {"side": side, "qty": qty}


def main() -> None:
    engine = PaperEngine()
    trades = load_spy_paper_trades()

    dst = Path("logs") / "spy_phase5_paperlive_results.jsonl"
    out_f = dst.open("w", encoding="utf-8")

    print(f"Loaded {len(trades)} SPY paper trade candidates.")

    for idx, row in enumerate(trades, start=1):
        ts = row.get("ts")
        info = infer_side_and_qty(row)
        side = info["side"]
        qty = info["qty"]

        # Call Phase-5 + risk hook wrapper
        result = place_order_phase5(
            engine,
            symbol="SPY",
            entry_ts=ts,
            side=side,
            qty=qty,
            price=row.get("price"),
            regime="SPY_ORB_REPLAY",
        )

        details = None
        if isinstance(result, dict):
            details = (
                result.get("phase5_details")
                or result.get("risk_details")
                or result.get("details")
            )

        ev = None
        ev_band_abs = None
        if isinstance(details, dict):
            ev = details.get("ev_mu")
            ev_band_abs = details.get("ev_band_abs")

        # --- SPY EV-diagnostics + Kelly (log-only) ---

        # For now, SPY paper runner has no true realized PnL; use 0.0 placeholder.
        realized_pnl_paper = 0.0

        # Safe EV value
        try:
            ev_val = float(ev) if ev is not None else 0.0
        except (TypeError, ValueError):
            ev_val = 0.0

        # EV-gap vs realized (placeholder)
        ev_gap_abs = abs(ev_val - realized_pnl_paper)
        ev_hit_flag = ev_gap_abs >= 0.20  # same soft-veto threshold as NVDA

        # Price and Kelly-style suggestion (log-only, does NOT change behaviour)
        price_val = row.get("price")
        try:
            price_f = float(price_val) if price_val is not None else 0.0
        except (TypeError, ValueError):
            price_f = 0.0

        try:
            risk_per_trade = float(os.environ.get("HAT_PHASE5_SPY_RISK_PER_TRADE", "50.0"))
        except (TypeError, ValueError):
            risk_per_trade = 50.0

        if price_f > 0.0:
            stop_fraction = 0.01
            stop_dollars = max(price_f * stop_fraction, 0.01)
            kelly_suggested_qty = risk_per_trade / stop_dollars
        else:
            kelly_suggested_qty = 1.0

        # Clamp to a safe band
        if kelly_suggested_qty < 1.0:
            kelly_suggested_qty = 1.0
        if kelly_suggested_qty > 100.0:
            kelly_suggested_qty = 100.0

        # For now, keep the original qty as the used quantity
        try:
            qty_used = float(qty)
        except (TypeError, ValueError):
            qty_used = 0.0

        out = {
            "idx": idx,
            "ts_trade": ts,
            "symbol": "SPY",
            "side": side,
            "qty": qty,
            "price": row.get("price"),
            "ev": ev,
            "ev_band_abs": ev_band_abs,
            "realized_pnl_paper": realized_pnl_paper,
            "ev_gap_abs": ev_gap_abs,
            "ev_hit_flag": ev_hit_flag,
            "qty_used": qty_used,
            "kelly_suggested_qty": kelly_suggested_qty,
            "phase5_result": result,
            "position_after": engine.positions.get("SPY", 0.0),
        }
        out_f.write(json.dumps(out) + "\n")

    out_f.close()
    print(f"Wrote SPY Phase-5 paper-live results to {dst}")


if __name__ == "__main__":
    main()