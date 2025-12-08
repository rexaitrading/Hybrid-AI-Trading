"""
PaperLiveWithoutIBG NVDA Phase-5 runner.

- NO broker / NO IBG; this is a pure in-process paper runner.
- Reads NVDA candidate trades from logs/paper_trades.jsonl.
- For each NVDA row, calls place_order_phase5(engine, ...) to apply:
  - Phase-5 decisions gate (from nvda_phase5_decisions.json),
  - RiskManager.phase5_no_averaging_down_for_symbol (if implemented).
- Logs decisions/results to logs/nvda_phase5_paperlive_results.jsonl.

This variant also simulates a simple exit:
- For each BUY entry, we add a synthetic SELL exit at a slightly higher price
  so that realized_pnl (fractional PnL, e.g. ~0.02) can flow into the CSV/EV report.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from hybrid_ai_trading.execution.execution_engine_phase5_guard import (
    place_order_phase5_with_guard as place_order_phase5,
)
from hybrid_ai_trading.risk.risk_manager import RiskManager


class PaperEngine:
    """
    Minimal in-process engine for paper trading without IBG.

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
        if hasattr(self.risk_manager, "positions"):
            setattr(self.risk_manager, "positions", self.positions)
        # Configure Phase-5 daily loss cap for paper runs.
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
        symbol = str(kwargs.get("symbol") or kwargs.get("sym") or "NVDA")
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

        self.positions[symbol] = pos

        return {
            "status": "filled",
            "engine_called": True,
            "symbol": symbol,
            "side": side,
            "qty": qty_f,
            "new_position": pos,
            "mode": "paper",
        }


def load_nvda_paper_trades() -> List[Dict[str, Any]]:
    """
    Load NVDA rows from logs/paper_trades.jsonl and sort by ts ascending.
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
            if str(row.get("symbol", "")).upper() != "NVDA":
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


def _make_log_record(
    idx: int,
    base_row: Dict[str, Any],
    result: Dict[str, Any],
    side: str,
    qty: float,
    price: float,
) -> Dict[str, Any]:
    """
    Flatten the place_order_phase5 result into a JSONL record that
    nvda_phase5_paper_to_csv.py can understand.
    """
    ts = result.get("ts") or base_row.get("ts")

    ev_value = (
        result.get("ev")
        or result.get("ev_mu")
        or (result.get("ev_info") or {}).get("mu")
    )
    ev_band_abs = (
        result.get("ev_band_abs")
        or result.get("ev_band")
        or (result.get("ev_info") or {}).get("band_abs")
        or (result.get("ev_info") or {}).get("band")
    )

    order_result = result.get("order_result") or {}

    out: Dict[str, Any] = {
        "idx": idx,
        "ts": ts,
        "entry_ts": result.get("entry_ts") or base_row.get("ts"),
        "symbol": result.get("symbol", "NVDA"),
        "regime": result.get("regime", "NVDA_BPLUS_LIVE"),
        "side": result.get("side") or side,
        "qty": result.get("qty") or qty,
        "price": result.get("price") or price,
        "order_result": order_result,
        "realized_pnl": result.get("realized_pnl"),
        "ev": ev_value,
        "ev_band_abs": ev_band_abs,
        "phase5_result": result,
        "position_after": result.get("position_after"),
    }
    return out


def main() -> None:
    engine = PaperEngine()
    trades = load_nvda_paper_trades()

    dst = Path("logs") / "nvda_phase5_paperlive_results.jsonl"
    dst.parent.mkdir(parents=True, exist_ok=True)
    out_f = dst.open("w", encoding="utf-8")

    print(f"Loaded {len(trades)} NVDA paper trade candidates.")

    for idx, row in enumerate(trades, start=1):
        ts = row.get("ts")
        base_price = float(row.get("price") or 1.0)
        info = infer_side_and_qty(row)
        entry_side = info["side"]
        qty = float(info["qty"])

        # 1) ENTRY: use inferred side and price from paper_trades
        entry_result: Dict[str, Any] = place_order_phase5(
            engine,
            symbol="NVDA",
            entry_ts=ts,
            side=entry_side,
            qty=qty,
            price=base_price,
            regime="NVDA_BPLUS_LIVE",
        )

        # For entry leg, realized_pnl = 0.0
        entry_result["realized_pnl"] = entry_result.get("realized_pnl", 0.0)

        entry_record = _make_log_record(
            idx=idx,
            base_row=row,
            result=entry_result,
            side=entry_side,
            qty=qty,
            price=base_price,
        )
        entry_record["position_after"] = engine.positions.get("NVDA", 0.0)
        out_f.write(json.dumps(entry_record) + "\n")

        # 2) EXIT: if entry was BUY, synthesize a SELL with a small profit
        if entry_side == "BUY":
            exit_price = base_price * 1.02  # +2% move for demo

            # Realized PnL as FRACTION (roughly 0.02 for +2% move)
            realized_pnl = (exit_price - base_price) / base_price

            exit_result: Dict[str, Any] = place_order_phase5(
                engine,
                symbol="NVDA",
                entry_ts=ts,
                side="SELL",
                qty=qty,
                price=exit_price,
                regime="NVDA_BPLUS_LIVE",
            )
            # Inject realized_pnl so CSV + EV report can see it
            exit_result["realized_pnl"] = realized_pnl

            exit_record = _make_log_record(
                idx=idx,
                base_row=row,
                result=exit_result,
                side="SELL",
                qty=qty,
                price=exit_price,
            )
            exit_record["position_after"] = engine.positions.get("NVDA", 0.0)
            out_f.write(json.dumps(exit_record) + "\n")

    out_f.close()
    print(f"Wrote NVDA Phase-5 paper-live results to {dst}")


if __name__ == "__main__":
    main()