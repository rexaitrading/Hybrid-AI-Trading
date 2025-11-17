# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import os
import pathlib
from typing import Any, Dict, List

from hybrid_ai_trading.runners.paper_config import load_config
from hybrid_ai_trading.runners.paper_logger import JsonlLogger
from hybrid_ai_trading.runners.paper_quantcore import run_once
from hybrid_ai_trading.utils.backtest_io import load_csv, row_to_snapshot


def main():
    ap = argparse.ArgumentParser("Backtest Replay")
    ap.add_argument("--config", default="config/paper_runner.yaml")
    ap.add_argument(
        "--input", required=True, help="CSV file with ts,symbol,price/last/close/vwap,"
    )
    ap.add_argument("--log", default="logs/backtest.jsonl")
    ap.add_argument(
        "--batch", type=int, default=100, help="Snapshots per run_once batch"
    )
    args = ap.parse_args()

    cfg = load_config(args.config)
    logger = JsonlLogger(args.log)

    buf: List[Dict[str, Any]] = []
    totals = {"rows": 0, "batches": 0, "decisions": 0}
    for row in load_csv(args.input):
        snap = row_to_snapshot(row)
        totals["rows"] += 1
        if not snap.get("symbol"):
            continue
        buf.append(snap)
        if len(buf) >= args.batch:
            res = run_once(cfg, logger, snapshots=buf)
            n = len(res.get("decisions", []))
            totals["decisions"] += n
            totals["batches"] += 1
            logger.info("bt_batch", size=len(buf), decisions=n)
            buf = []

    if buf:
        res = run_once(cfg, logger, snapshots=buf)
        n = len(res.get("decisions", []))
        totals["decisions"] += n
        totals["batches"] += 1
        logger.info("bt_batch", size=len(buf), decisions=n)

    print(json.dumps({"summary": totals}, indent=2))


if __name__ == "__main__":
    main()
