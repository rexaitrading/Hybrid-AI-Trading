from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from hybrid_ai_trading.replay.nvda_bplus_gate_score import compute_ev_from_trade


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    val = os.environ.get(name)
    if not val:
        return default
    try:
        return float(val)
    except ValueError:
        return default


def load_trades(jsonl_path: Path, limit: int = 0) -> List[Dict[str, Any]]:
    trades: List[Dict[str, Any]] = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                print("[EVLOG] WARN: Skipping invalid JSON line.")
                continue
            trades.append(obj)
            if limit > 0 and len(trades) >= limit:
                break
    return trades


def compute_summary(trades: List[Dict[str, Any]]) -> Dict[str, float]:
    if not trades:
        return {
            "n": 0,
            "mean_pnl_pct": 0.0,
            "mean_ev": 0.0,
        }

    n = len(trades)
    pnl = []
    evs = []

    for t in trades:
        g = _safe_float(t.get("gross_pnl_pct", 0.0), 0.0)
        pnl.append(g)
        ev = compute_ev_from_trade(t)
        evs.append(ev)

    mean_pnl = sum(pnl) / n if n else 0.0
    mean_ev = sum(evs) / n if n else 0.0

    return {
        "n": n,
        "mean_pnl_pct": mean_pnl,
        "mean_ev": mean_ev,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Log EV tuning runs (mean_pnl_pct and mean_ev) along with cost parameters."
    )
    parser.add_argument(
        "--jsonl",
        required=True,
        help="Path to replay trades JSONL.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit on number of trades to read (0 = no limit).",
    )
    parser.add_argument(
        "--note",
        type=str,
        default="",
        help="Optional free-form note for this run (e.g. 'slip=1.5bp test').",
    )
    args = parser.parse_args()

    jsonl_path = Path(args.jsonl)
    if not jsonl_path.exists():
        print("[EVLOG] ERROR: JSONL not found:", jsonl_path)
        return

    trades = load_trades(jsonl_path, limit=args.limit)
    summary = compute_summary(trades)

    n = summary["n"]
    mean_pnl = summary["mean_pnl_pct"]
    mean_ev = summary["mean_ev"]

    slippage_bp = _env_float("HAT_COST_DEFAULT_SLIPPAGE_BP", 0.0)
    fee_bp = _env_float("HAT_COST_DEFAULT_FEE_BP", 0.0)
    fee_per_share = _env_float("HAT_COST_DEFAULT_FEE_PER_SHARE", 0.0)

    symbol = "UNKNOWN"
    if trades:
        symbol = str(trades[0].get("symbol") or "UNKNOWN")

    ts = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    repo_root = Path(__file__).resolve().parent.parent
    log_dir = repo_root / "intel"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "ev_tuning_log.csv"

    file_exists = log_path.exists()

    row = [
        ts,
        symbol,
        str(jsonl_path),
        n,
        f"{mean_pnl:.6f}",
        f"{mean_ev:.6f}",
        f"{slippage_bp:.4f}",
        f"{fee_bp:.4f}",
        f"{fee_per_share:.6f}",
        args.note,
    ]

    with log_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(
                [
                    "ts_utc",
                    "symbol",
                    "jsonl_path",
                    "n_trades",
                    "mean_pnl_pct",
                    "mean_ev",
                    "slippage_bp",
                    "fee_bp",
                    "fee_per_share",
                    "note",
                ]
            )
        writer.writerow(row)

    print("[EVLOG] Appended row to", log_path)
    print("[EVLOG] ts_utc=", ts)
    print("[EVLOG] symbol=", symbol)
    print("[EVLOG] n_trades=", n)
    print("[EVLOG] mean_pnl_pct=", mean_pnl)
    print("[EVLOG] mean_ev=", mean_ev)
    print("[EVLOG] slippage_bp=", slippage_bp, "fee_bp=", fee_bp, "fee_per_share=", fee_per_share)
    if args.note:
        print("[EVLOG] note=", args.note)


if __name__ == "__main__":
    main()