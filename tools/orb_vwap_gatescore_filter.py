from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser("ORB/VWAP GateScore + cost filter for enriched JSONL trades")
    ap.add_argument(
        "--jsonl",
        required=True,
        help="Input enriched JSONL (e.g. research/aapl_orb_vwap_replay_trades_enriched.jsonl)",
    )
    ap.add_argument(
        "--config",
        required=True,
        help="Threshold config JSON (e.g. config/orb_vwap_aapl_thresholds.json)",
    )
    ap.add_argument(
        "--out",
        required=True,
        help="Output gated JSONL path (e.g. research/aapl_orb_vwap_replay_trades_gated.jsonl)",
    )
    return ap.parse_args(argv)


def load_thresholds(config_path: str) -> Dict[str, Any]:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Threshold config not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg


def load_trades(jsonl_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(jsonl_path):
        raise FileNotFoundError(f"JSONL not found: {jsonl_path}")
    trades: List[Dict[str, Any]] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                trades.append(rec)
            except Exception as exc:
                print(f"[GATE-FILTER] ERROR parsing line {line_no}: {exc}")
    return trades


def _safe_float(d: Dict[str, Any], key: str, default: float = 0.0) -> float:
    v = d.get(key, default)
    try:
        return float(v)
    except Exception:
        return default


def filter_trades(trades: List[Dict[str, Any]], thresholds: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Thresholds from config
    edge_min = float(thresholds.get("gatescore_edge_ratio_min", 0.0))
    max_cost_bp = float(thresholds.get("max_cost_bp", 1e9))
    min_pnl_training = float(thresholds.get("min_pnl_pct_training", -1.0))

    print("[GATE-FILTER] Using thresholds from config:")
    print("  gatescore_edge_ratio_min =", edge_min)
    print("  max_cost_bp              =", max_cost_bp)
    print("  min_pnl_pct_training     =", min_pnl_training)

    gated: List[Dict[str, Any]] = []
    for rec in trades:
        er = _safe_float(rec, "gatescore_edge_ratio", 0.0)
        cost_bp = _safe_float(rec, "cost_bp", 0.0)
        pnl_pct = _safe_float(rec, "pnl_pct", 0.0)

        if er < edge_min:
            continue
        if cost_bp > max_cost_bp:
            continue
        if pnl_pct < min_pnl_training:
            continue

        gated.append(rec)

    return gated


def save_trades(jsonl_path: str, trades: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(jsonl_path), exist_ok=True)
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for rec in trades:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main() -> None:
    args = parse_args()
    thresholds = load_thresholds(args.config)
    trades = load_trades(args.jsonl)
    print(f"[GATE-FILTER] Loaded {len(trades)} trade(s) from {args.jsonl}")
    gated = filter_trades(trades, thresholds)
    print(f"[GATE-FILTER] {len(gated)} trade(s) passed thresholds.")
    save_trades(args.out, gated)
    print(f"[GATE-FILTER] Wrote gated trades to {args.out}")


if __name__ == "__main__":
    main()