from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, Optional

import pandas as pd  # type: ignore[import]


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser("Enrich AAPL ORB/VWAP trades JSONL with PnL and EV using bar data")
    ap.add_argument(
        "--jsonl",
        default=os.path.join("research", "aapl_orb_vwap_replay_trades.jsonl"),
        help="Input JSONL of AAPL ORB/VWAP trades (default: research/aapl_orb_vwap_replay_trades.jsonl)",
    )
    ap.add_argument(
        "--bars",
        default=os.path.join("data", "AAPL_1m.csv"),
        help="AAPL 1m bar CSV (default: data/AAPL_1m.csv)",
    )
    ap.add_argument(
        "--out",
        default=os.path.join("research", "aapl_orb_vwap_replay_trades_enriched.jsonl"),
        help="Output enriched JSONL (default: research/aapl_orb_vwap_replay_trades_enriched.jsonl)",
    )
    return ap.parse_args(argv)


def _find_timestamp_column(df: pd.DataFrame) -> str:
    candidates = ["ts", "timestamp", "datetime", "time"]
    for c in candidates:
        if c in df.columns:
            return c
    # Fallback: first column that looks like a timestamp
    for col in df.columns:
        if "time" in col.lower() or "date" in col.lower():
            return col
    raise ValueError(
        f"Could not find a timestamp column in AAPL bars. "
        f"Expected one of: {candidates}, got columns={list(df.columns)}"
    )


def _parse_iso_dt(s: str) -> pd.Timestamp:
    # Handle strings like "2025-01-02 14:36:00+00:00"
    return pd.to_datetime(s)


def _compute_pnl_pct(entry_px: float, exit_px: float, side: str) -> float:
    if entry_px <= 0.0:
        return 0.0
    side_up = (side or "").upper()
    if side_up in ("BUY", "LONG"):
        return (exit_px - entry_px) / entry_px
    elif side_up in ("SELL", "SHORT"):
        return (entry_px - exit_px) / entry_px
    else:
        # Unknown side: be conservative
        return 0.0


def _compute_ev(pnl_pct: float, cost_bp: Optional[float]) -> float:
    if cost_bp is None:
        return pnl_pct
    return pnl_pct - (float(cost_bp) / 10_000.0)


def enrich_jsonl(jsonl_path: str, bars_path: str, out_path: str) -> None:
    if not os.path.exists(jsonl_path):
        raise FileNotFoundError(f"Input JSONL not found: {jsonl_path}")
    if not os.path.exists(bars_path):
        raise FileNotFoundError(f"AAPL bars CSV not found: {bars_path}")

    print(f"[AAPL-ENRICH] Loading bars from {bars_path} ...")
    bars_df = pd.read_csv(bars_path)
    ts_col = _find_timestamp_column(bars_df)
    if "close" not in bars_df.columns:
        raise ValueError(f"[AAPL-ENRICH] Expected 'close' column in bars CSV, got columns={list(bars_df.columns)}")

    # Parse timestamps
    bars_df[ts_col] = pd.to_datetime(bars_df[ts_col])

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    n_in = 0
    n_out = 0
    n_failed = 0

    print(f"[AAPL-ENRICH] Reading trades from {jsonl_path} ...")
    with open(jsonl_path, "r", encoding="utf-8") as src, open(out_path, "w", encoding="utf-8") as dst:
        for line in src:
            line = line.strip()
            if not line:
                continue
            n_in += 1
            try:
                rec: Dict[str, Any] = json.loads(line)
            except Exception as exc:
                print(f"[AAPL-ENRICH] ERROR parsing JSONL line {n_in}: {exc}")
                n_failed += 1
                continue

            entry_ts_str = rec.get("entry_ts")
            session_open_str = rec.get("session_open")
            side = rec.get("side", "BUY")
            cost_bp = rec.get("cost_bp")

            if not entry_ts_str or not session_open_str:
                # Missing timestamps, just passthrough record unchanged
                dst.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n_out += 1
                continue

            try:
                entry_ts = _parse_iso_dt(entry_ts_str)
                session_open = _parse_iso_dt(session_open_str)
            except Exception as exc:
                print(f"[AAPL-ENRICH] ERROR parsing timestamps for line {n_in}: {exc}")
                dst.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n_out += 1
                n_failed += 1
                continue

            session_date = session_open.normalize()  # midnight of that day

            # Filter bars for that session date
            session_mask = (bars_df[ts_col].dt.normalize() == session_date)
            session_bars = bars_df[session_mask].copy()

            if session_bars.empty:
                print(f"[AAPL-ENRICH] No bars found for session date {session_date.date()} (line {n_in})")
                dst.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n_out += 1
                n_failed += 1
                continue

            # Find entry bar: exact match first, then first bar after entry_ts
            entry_match = session_bars[session_bars[ts_col] == entry_ts]
            if entry_match.empty:
                entry_match = session_bars[session_bars[ts_col] >= entry_ts].head(1)

            if entry_match.empty:
                print(f"[AAPL-ENRICH] Could not find entry bar at/after {entry_ts} in session {session_date.date()} (line {n_in})")
                dst.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n_out += 1
                n_failed += 1
                continue

            entry_row = entry_match.iloc[0]
            entry_px = float(entry_row["close"])
            entry_ts_bar = entry_row[ts_col]

            # Exit at last bar of the session
            exit_row = session_bars.iloc[-1]
            exit_px = float(exit_row["close"])
            exit_ts_bar = exit_row[ts_col]

            pnl_pct = _compute_pnl_pct(entry_px=entry_px, exit_px=exit_px, side=side)
            ev = _compute_ev(pnl_pct, cost_bp)

            # Attach enrichment fields
            rec["entry_px"] = entry_px
            rec["exit_px"] = exit_px
            rec["entry_ts_bar"] = entry_ts_bar.isoformat()
            rec["exit_ts_bar"] = exit_ts_bar.isoformat()
            rec["pnl_pct"] = pnl_pct
            rec["ev"] = ev

            dst.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_out += 1

    print(f"[AAPL-ENRICH] Read {n_in} trade record(s) from {jsonl_path}")
    print(f"[AAPL-ENRICH] Wrote {n_out} enriched record(s) to {out_path}")
    if n_failed:
        print(f"[AAPL-ENRICH] {n_failed} record(s) failed enrichment; original fields were preserved for those.")
    

def main() -> None:
    args = parse_args()
    enrich_jsonl(jsonl_path=args.jsonl, bars_path=args.bars, out_path=args.out)


if __name__ == "__main__":
    main()