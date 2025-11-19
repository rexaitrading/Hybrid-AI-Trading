from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from tools.orb_vwap_gatescore_filter import filter_trades
from hybrid_ai_trading.trade_engine_phase5_skeleton import TradeEnginePhase5
from hybrid_ai_trading.risk_manager_phase5_bridge import PositionSnapshot, AddRequest


def _load_thresholds(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_trades(jsonl_path: str) -> List[Dict[str, Any]]:
    trades: List[Dict[str, Any]] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            trades.append(json.loads(line))
    return trades


def _append_mock_paper_event(path: str, event: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def main() -> None:
    cfg_path = os.path.join("config", "orb_vwap_aapl_thresholds.json")
    thresholds = _load_thresholds(cfg_path)

    jsonl_path = os.path.join("research", "aapl_orb_vwap_replay_trades_enriched.jsonl")
    trades = _load_trades(jsonl_path)

    gated = filter_trades(trades, thresholds)

    engine = TradeEnginePhase5()
    paper_log_path = os.path.join("logs", "paper_exec_phase5_mock.jsonl")

    current_notional = 0.0
    order_id = 0

    for t in gated:
        symbol = t.get("symbol", "AAPL")
        side = "LONG"
        pnl_pct = float(t.get("pnl_pct", 0.0))
        unrealized_pnl_bp = pnl_pct * 10_000.0
        base_notional = float(t.get("cost_notional") or 10_000.0)

        if current_notional == 0.0:
            current_notional = base_notional

        pos = PositionSnapshot(
            symbol=symbol,
            side=side,
            unrealized_pnl_bp=unrealized_pnl_bp,
            notional=current_notional,
        )
        add_req = AddRequest(
            additional_notional=base_notional,
            additional_shares_round_trip=100,
        )

        decision = engine.consider_add(pos, add_req)

        order_id += 1
        event: Dict[str, Any] = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "notional_before": current_notional,
            "add_notional": base_notional,
            "unrealized_pnl_bp": unrealized_pnl_bp,
            "can_add": decision.can_add,
            "reason": decision.reason,
            "phase": "phase5_orb_vwap_sim",
        }

        if decision.can_add:
            current_notional += base_notional
            event["notional_after"] = current_notional
            event["executed"] = True
        else:
            event["notional_after"] = current_notional
            event["executed"] = False

        _append_mock_paper_event(paper_log_path, event)

    print(f"[AAPL-PAPER-MOCK] Wrote mock paper events to {paper_log_path}")


if __name__ == "__main__":
    main()