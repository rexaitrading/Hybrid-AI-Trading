# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Tuple

from hybrid_ai_trading.runners.paper_config import load_config
from hybrid_ai_trading.runners.paper_logger import JsonlLogger
from hybrid_ai_trading.runners.paper_quantcore import run_once

# --- Phase1: deterministic replay metrics (no fabrication) ---
from collections import defaultdict, deque
import math

def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x

def _edge_micro_from_prices(prices, lookback: int = 30) -> tuple[float, float]:
    # Need enough history
    if prices is None or len(prices) < max(2, lookback):
        return 0.0, 0.0
    p0 = float(list(prices)[-lookback])
    p1 = float(list(prices)[-1])
    if p0 <= 0.0:
        return 0.0, 0.0
    r = (p1 / p0) - 1.0  # raw return

    # Vol proxy: stdev of 1-step returns in the same window
    w = list(prices)[-lookback:]
    rets = []
    for j in range(1, len(w)):
        a = float(w[j-1])
        b = float(w[j])
        if a > 0.0:
            rets.append((b / a) - 1.0)
    if len(rets) < 2:
        vol = 0.0
    else:
        m = sum(rets) / len(rets)
        v = sum((x - m) * (x - m) for x in rets) / max(1, (len(rets) - 1))
        vol = math.sqrt(v)

    # edge_ratio: bounded signed return proxy
    edge = _clamp(r, -0.05, 0.05)  # +/-5% cap

    # micro_score: signal-to-noise proxy (bounded 0..1)
    snr = abs(r) / (vol + 1e-6)
    micro = _clamp(snr / 10.0, 0.0, 1.0)  # scale

    return float(edge), float(micro)
# --- end Phase1 metrics ---

from hybrid_ai_trading.utils.backtest_io import load_csv, row_to_snapshot


def _build_risk_mgr(cfg: Dict[str, Any]):
    """
    Provide a risk manager object. paper_quantcore will fallback to DummyRiskMgr if needed,
    but we keep this hook for future Phase5 wiring.
    """
    try:
        from hybrid_ai_trading.risk.risk_manager import RiskManager  # type: ignore
        return RiskManager(cfg)  # type: ignore
    except Exception:
        # allow None; paper_quantcore._ensure_risk_mgr will wrap to DummyRiskMgr approve-all
        return None


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


def _run_ticks(buf: List[Dict[str, Any]], logger: JsonlLogger, risk_mgr: Any) -> Tuple[int, int, int]:
    ticks = 0
    decisions = 0
    logged = 0

    for snap in buf:
        sym = str(snap.get("symbol", "")).upper().strip()
        if not sym:
            continue

        px = _snap_price(snap)
        if px is None:
            continue

        # Evaluate one tick
        out = run_once([sym], {sym: px}, risk_mgr)
        ticks += 1

        # Expect: list[{"symbol":..., "decision":{...}}]
        try:
            if isinstance(out, list) and out and isinstance(out[0], dict) and "decision" in out[0]:
                decisions += 1
                # Track rolling prices per symbol for deterministic metrics
                if not hasattr(risk_mgr, '_hat_price_hist'):
                    risk_mgr._hat_price_hist = defaultdict(lambda: deque(maxlen=400))
                hist = risk_mgr._hat_price_hist[sym]
                hist.append(float(px))
                edge_ratio, micro_score = _edge_micro_from_prices(hist, lookback=30)

                # as_of_date: best-effort (events_from_replay will fallback to replay_session date)
                as_of = str(getattr(risk_mgr, 'as_of_date', '') or '')

                payload = {
                    'symbol': sym,
                    'price': px,
                    'decision': out[0].get('decision'),
                    'as_of_date': as_of,
                    'edge_ratio': edge_ratio,
                    'micro_score': micro_score,
                    'realized_pnl': None,
                    'pnl_samples': 0,
                    'source': 'replay',
                }
                logger.info('bt_decision', **payload)
                logged += 1
        except Exception:
            pass

    return ticks, decisions, logged


def main():
    ap = argparse.ArgumentParser("Backtest Replay")
    ap.add_argument("--config", default="config/paper_runner.yaml")
    ap.add_argument("--input", required=True, help="CSV file with ts,symbol,price/last/close/vwap,...")
    ap.add_argument("--log", default="logs/backtest.jsonl")
    ap.add_argument("--batch", type=int, default=100, help="Snapshots per batch (progress/logging)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    logger = JsonlLogger(args.log)
    risk_mgr = _build_risk_mgr(cfg)

    totals = {"rows": 0, "ticks": 0, "decisions": 0, "logged": 0, "batches": 0}

    buf: List[Dict[str, Any]] = []
    for row in load_csv(args.input):
        snap = row_to_snapshot(row)
        totals["rows"] += 1
        if not snap.get("symbol"):
            continue
        buf.append(snap)

        if len(buf) >= args.batch:
            t, d, l = _run_ticks(buf, logger, risk_mgr)
            totals["ticks"] += t
            totals["decisions"] += d
            totals["logged"] += l
            totals["batches"] += 1
            logger.info("bt_batch", size=len(buf), ticks=t, decisions=d)
            buf = []

    if buf:
        t, d, l = _run_ticks(buf, logger, risk_mgr)
        totals["ticks"] += t
        totals["decisions"] += d
        totals["logged"] += l
        totals["batches"] += 1
        logger.info("bt_batch", size=len(buf), ticks=t, decisions=d)

    print(json.dumps({"summary": totals}, indent=2))

    # FAIL-CLOSED: if we processed ticks but produced no decisions, it's not Phase1 DONE.
    if totals["ticks"] > 0 and totals["decisions"] == 0:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
