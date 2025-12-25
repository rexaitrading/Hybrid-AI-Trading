# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

from hybrid_ai_trading.runners.paper_config import load_config
from hybrid_ai_trading.runners.paper_logger import JsonlLogger
from hybrid_ai_trading.runners.paper_quantcore import run_once
from hybrid_ai_trading.utils.backtest_io import load_csv, row_to_snapshot


def _decision_is_actionable(dec: Dict[str, Any] | None) -> bool:
    if not isinstance(dec, dict):
        return False
    action = str(dec.get("action", "")).upper().strip()
    return action in {"BUY", "SELL", "SHORT", "COVER", "LONG", "EXIT"}


def main() -> int:
    ap = argparse.ArgumentParser("Backtest Replay")
    ap.add_argument("--config", default="config/paper_runner.yaml")
    ap.add_argument("--input", required=True, help="CSV file with ts,symbol,price/last/close/vwap,")
    ap.add_argument("--log", default="logs/backtest.jsonl")
    ap.add_argument("--batch", type=int, default=100, help="Snapshots per run_once batch")
    args = ap.parse_args()

    cfg = load_config(args.config)
    # paper_quantcore._ensure_risk_mgr is tolerant; pass config risk dict if present.
    risk_cfg = (cfg or {}).get("risk", {}) if isinstance(cfg, dict) else {}

    logger = JsonlLogger(args.log)

    rows = load_csv(args.input)
    snapshots: List[Dict[str, Any]] = []
    for r in rows:
        try:
            snapshots.append(row_to_snapshot(r))
        except Exception:
            # skip malformed rows (fail-closed is handled by decisions outcome)
            continue

    price_map: Dict[str, float] = {}
    seen_symbols: List[str] = []
    actionable = False
    total_rows = 0
    total_batches = 0
    total_decisions = 0

    bsz = max(1, int(args.batch))

    for snap in snapshots:
        total_rows += 1
        sym = str(snap.get("symbol", "")).upper().strip()
        if not sym:
            continue
        px = snap.get("price")
        try:
            px_f = float(px)
        except Exception:
            continue

        if sym not in price_map:
            seen_symbols.append(sym)
        price_map[sym] = px_f

        if (total_rows % bsz) == 0:
            total_batches += 1
            decisions = run_once(list(price_map.keys()), price_map, risk_cfg)
            if isinstance(decisions, list):
                total_decisions += len(decisions)
                for d in decisions:
                    try:
                        logger.info("decision", decision=d)
                    except Exception:
                        pass
                    if isinstance(d, dict) and _decision_is_actionable(d.get("decision")):
                        actionable = True

    # final flush
    if total_rows % bsz != 0:
        total_batches += 1
        decisions = run_once(list(price_map.keys()), price_map, risk_cfg)
        if isinstance(decisions, list):
            total_decisions += len(decisions)
            for d in decisions:
                try:
                    logger.info("decision", decision=d)
                except Exception:
                    pass
                if isinstance(d, dict) and _decision_is_actionable(d.get("decision")):
                    actionable = True

    summary = {
        "summary": {
            "rows": total_rows,
            "batches": total_batches,
            "symbols": seen_symbols,
            "decisions": total_decisions,
            "actionable": actionable,
        }
    }
    print(json.dumps(summary, ensure_ascii=False))

    # Smoke test accepts 0 (decisions found) or 2 (fail-closed: no decisions)
    return 0 if actionable else 2


if __name__ == "__main__":
    raise SystemExit(main())

