from __future__ import annotations

import argparse
import glob
import json
import os
from typing import Any, Dict, Optional


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser("Convert ORB/VWAP QQQ replay summaries to JSONL trades")
    ap.add_argument(
        "--pattern",
        default="orb_vwap_replay_summary_QQQ_*.json",
        help="Glob pattern for QQQ ORB/VWAP summary JSON files (default: orb_vwap_replay_summary_QQQ_*.json)",
    )
    ap.add_argument(
        "--out",
        default=os.path.join("research", "qqq_orb_vwap_replay_trades.jsonl"),
        help="Output JSONL path (default: research/qqq_orb_vwap_replay_trades.jsonl)",
    )
    return ap.parse_args(argv)


def _safe_get(d: Dict[str, Any], *path: str, default: Any = None) -> Any:
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _compute_cost_bp(total_cost: Optional[float], notional: Optional[float]) -> Optional[float]:
    try:
        if total_cost is None or notional is None:
            return None
        notional_f = float(notional)
        if notional_f <= 0.0:
            return None
        return float(total_cost) / notional_f * 10_000.0
    except Exception:
        return None


def convert_summaries_to_jsonl(pattern: str, out_path: str) -> None:
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"[QQQ-ORB-JSONL] No files matched pattern: {pattern}")
        return

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    n_files = 0
    n_trades = 0

    with open(out_path, "w", encoding="utf-8") as out_f:
        for path in files:
            n_files += 1
            try:
                with open(path, "r", encoding="utf-8") as f:
                    summary = json.load(f)
            except Exception as exc:
                print(f"[QQQ-ORB-JSONL] ERROR reading {path}: {exc}")
                continue

            symbol = summary.get("symbol")
            has_signal = bool(summary.get("has_signal", False))

            if not has_signal:
                continue

            entry_ts = summary.get("entry_ts")
            side = summary.get("side")
            session_open = summary.get("session_open")
            expected_edge = summary.get("expected_edge")

            gs_score = _safe_get(summary, "gatescore", "score")
            gs_edge_ratio = _safe_get(summary, "gatescore", "edge_ratio")
            gs_allowed = _safe_get(summary, "gatescore", "allowed")
            gs_reason = _safe_get(summary, "gatescore", "reason")

            micro_last_ret = _safe_get(summary, "micro", "last_ret")
            micro_window_ret = _safe_get(summary, "micro", "window_ret")
            micro_volume_sum = _safe_get(summary, "micro", "volume_sum")
            micro_imbalance = _safe_get(summary, "micro", "imbalance")
            micro_signed_volume = _safe_get(summary, "micro", "signed_volume")
            micro_spread_now = _safe_get(summary, "micro", "spread_now")
            micro_spread_avg = _safe_get(summary, "micro", "spread_avg")
            micro_score = _safe_get(summary, "micro", "micro_score")

            cost_notional = _safe_get(summary, "cost", "notional")
            cost_spread_cost = _safe_get(summary, "cost", "spread_cost")
            cost_slippage_cost = _safe_get(summary, "cost", "slippage_cost")
            cost_fee_cost = _safe_get(summary, "cost", "fee_cost")
            cost_total_cost = _safe_get(summary, "cost", "total_cost")
            cost_bp = _compute_cost_bp(cost_total_cost, cost_notional)

            record = {
                "symbol": symbol,
                "session_open": session_open,
                "entry_ts": entry_ts,
                "side": side,
                "expected_edge": expected_edge,
                "used_fallback_orb": summary.get("used_fallback_orb"),
                "open_range_minutes": summary.get("open_range_minutes"),
                # GateScore
                "gatescore_score": gs_score,
                "gatescore_edge_ratio": gs_edge_ratio,
                "gatescore_allowed": gs_allowed,
                "gatescore_reason": gs_reason,
                # Microstructure
                "micro_last_ret": micro_last_ret,
                "micro_window_ret": micro_window_ret,
                "micro_volume_sum": micro_volume_sum,
                "micro_imbalance": micro_imbalance,
                "micro_signed_volume": micro_signed_volume,
                "micro_spread_now": micro_spread_now,
                "micro_spread_avg": micro_spread_avg,
                "micro_score": micro_score,
                # Cost
                "cost_notional": cost_notional,
                "cost_spread_cost": cost_spread_cost,
                "cost_slippage_cost": cost_slippage_cost,
                "cost_fee_cost": cost_fee_cost,
                "cost_total_cost": cost_total_cost,
                "cost_bp": cost_bp,
                # Provenance
                "source_file": os.path.basename(path),
            }

            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            n_trades += 1

    print(f"[QQQ-ORB-JSONL] Processed {n_files} summary files.")
    print(f"[QQQ-ORB-JSONL] Emitted {n_trades} trade record(s) to {out_path}")


def main() -> None:
    args = parse_args()
    convert_summaries_to_jsonl(pattern=args.pattern, out_path=args.out)


if __name__ == "__main__":
    main()