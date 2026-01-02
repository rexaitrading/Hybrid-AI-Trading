# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

from hybrid_ai_trading.runners.paper_config import load_config
from hybrid_ai_trading.runners.paper_logger import JsonlLogger

# --- Phase1: deterministic replay metrics (no fabrication) ---
from collections import defaultdict, deque
import math

_HAT_PRICE_HIST = defaultdict(lambda: deque(maxlen=400))

def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x

def _price_from_locals(L: dict) -> float | None:
    # Robustly discover current price from common local names
    for k in ('px_f','price','px','last','close','vwap'):
        v = L.get(k, None)
        if v is not None:
            try: return float(v)
            except Exception: pass
    for k in ('snap','snapshot','row'):
        v = L.get(k, None)
        if isinstance(v, dict):
            for kk in ('price','last','close','vwap','px'):
                vv = v.get(kk, None)
                if vv is not None:
                    try: return float(vv)
                    except Exception: pass
    return None

def _edge_micro_from_prices(prices, lookback: int = 30) -> tuple[float, float]:
    if prices is None or len(prices) < max(2, lookback):
        return 0.0, 0.0
    w = list(prices)[-lookback:]
    p0 = float(w[0])
    p1 = float(w[-1])
    if p0 <= 0.0:
        return 0.0, 0.0
    r = (p1 / p0) - 1.0
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
    edge = _clamp(r, -0.05, 0.05)
    snr = abs(r) / (vol + 1e-6)
    micro = _clamp(snr / 10.0, 0.0, 1.0)
    return float(edge), float(micro)
# --- end Phase1 metrics ---

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
        _HAT_PRICE_HIST[sym].append(float(px_f))

        if (total_rows % bsz) == 0:
            total_batches += 1
            decisions = run_once(list(price_map.keys()), price_map, risk_cfg)
            if isinstance(decisions, list):
                total_decisions += len(decisions)
                for d in decisions:
                    try:
                        # Enrich decision row with deterministic metrics used by GateScore replay->events
                        sym_u = str(d.get('symbol','') or '').upper().strip()
                        if not sym_u:
                            sym_u = str((d.get('decision') or {}).get('symbol','') or '').upper().strip()
                        px_now = _price_from_locals(locals())
                        if sym_u and (px_now is not None):
                            edge_ratio, micro_score = _edge_micro_from_prices(_HAT_PRICE_HIST[sym_u], lookback=30)
                            d['as_of_date'] = ''  # events_from_replay can fallback to replay_session.json
                            d['edge_ratio'] = float(edge_ratio)
                            d['micro_score'] = float(micro_score)
                            d['realized_pnl'] = None
                            d['pnl_samples'] = 0
                            d['source'] = 'replay'
                        logger.info('decision', decision=d)
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
                    # Enrich decision row with deterministic metrics used by GateScore replay->events
                    sym_u = str(d.get('symbol','') or '').upper().strip()
                    if not sym_u:
                        sym_u = str((d.get('decision') or {}).get('symbol','') or '').upper().strip()
                    px_now = _price_from_locals(locals())
                    if sym_u and (px_now is not None):
                        edge_ratio, micro_score = _edge_micro_from_prices(_HAT_PRICE_HIST[sym_u], lookback=30)
                        d['as_of_date'] = ''  # events_from_replay can fallback to replay_session.json
                        d['edge_ratio'] = float(edge_ratio)
                        d['micro_score'] = float(micro_score)
                        d['realized_pnl'] = None
                        d['pnl_samples'] = 0
                        d['source'] = 'replay'
                    logger.info('decision', decision=d)
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
