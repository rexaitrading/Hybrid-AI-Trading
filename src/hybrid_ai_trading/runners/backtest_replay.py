# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

from hybrid_ai_trading.runners.paper_config import load_config
from hybrid_ai_trading.runners.paper_logger import JsonlLogger
from hybrid_ai_trading.runners.paper_quantcore import run_once
from hybrid_ai_trading.utils.backtest_io import load_csv, row_to_snapshot


def _build_risk_mgr(cfg: Dict[str, Any]):
    """
    Build a risk manager compatible with run_once(symbols, price_map, risk_mgr).

    Fail-closed: if we can't construct it from current repo code, raise with a precise message.
    """
    # Pattern A: helper in paper_quantcore (preferred if present)
    try:
        from hybrid_ai_trading.runners import paper_quantcore as pq  # type: ignore
        if hasattr(pq, "build_risk_manager"):
            return pq.build_risk_manager(cfg)  # type: ignore
    except Exception:
        pass

    # Pattern B/C: RiskManager class
    try:
        from hybrid_ai_trading.risk.risk_manager import RiskManager  # type: ignore
        if hasattr(RiskManager, "from_config"):
            return RiskManager.from_config(cfg)  # type: ignore
        return RiskManager(cfg)  # type: ignore
    except Exception:
        pass

    raise RuntimeError(
        "Cannot construct risk_mgr for run_once(symbols, price_map, risk_mgr). "
        "Expected one of: paper_quantcore.build_risk_manager(cfg) OR "
        "risk_manager.RiskManager.from_config(cfg) OR RiskManager(cfg). "
        "Search paper_quantcore.py and risk/risk_manager.py for the real builder and patch _build_risk_mgr."
    )


def _snap_price(snap: Dict[str, Any]) -> float | None:
    px = snap.get("price")
    if px is None:
        px = snap.get("close")
    if px is None:
        px = snap.get("last")
    if px is None:
        px = snap.get("vwap")
    if px is None:
        return None
    try:
        return float(px)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser("Backtest Replay")
    ap.add_argument("--config", default="config/paper_runner.yaml")
    ap.add_argument("--input", required=True, help="CSV file with ts,symbol,price/last/close/vwap,...")
    ap.add_argument("--log", default="logs/backtest.jsonl")
    ap.add_argument("--batch", type=int, default=100, help="Snapshots per batch (for progress only)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    logger = JsonlLogger(args.log)
    risk_mgr = _build_risk_mgr(cfg)

    totals = {"rows": 0, "ticks": 0, "logged": 0}

    buf: List[Dict[str, Any]] = []
    for row in load_csv(args.input):
        snap = row_to_snapshot(row)
        totals["rows"] += 1
        if not snap.get("symbol"):
            continue
        buf.append(snap)

        if len(buf) >= args.batch:
            totals["ticks"] += _run_ticks(buf, logger, risk_mgr)
            logger.info("bt_batch", size=len(buf))
            buf = []

    if buf:
        totals["ticks"] += _run_ticks(buf, logger, risk_mgr)
        logger.info("bt_batch", size=len(buf))

    print(json.dumps({"summary": totals}, indent=2))


def _run_ticks(buf: List[Dict[str, Any]], logger: JsonlLogger, risk_mgr: Any) -> int:
    ticks = 0
    for snap in buf:
        sym = str(snap.get("symbol", "")).upper().strip()
        if not sym:
            continue
        px = _snap_price(snap)
        if px is None:
            continue

        symbols = [sym]
        price_map = {sym: px}

        res = run_once(symbols, price_map, risk_mgr)
        ticks += 1

        if res is not None:
            try:
                logger.log(res)
            except Exception:
                pass

    return ticks


if __name__ == "__main__":
    main()