#!/usr/bin/env python3
"""
Loose NVDA B+ replay driver.

- Calls the original tools/sim_nvda_bplus_replay.py with the given arguments.
- If it generates at least one record in the output JSONL, we keep it.
- If it generates NO trades (empty or missing JSONL), we synthesize a single
  fallback trade record using the first row of the CSV.

This is for wiring / tuning only, so you can see NVDA trades flowing through
Phase-5 enrichment and into Notion, even while heuristics are still being tuned.
"""

import argparse
import csv
import json
import os
import subprocess
import sys
from typing import Any, Dict


def synthesize_fallback_trade(csv_path: str, symbol: str) -> Dict[str, Any]:
    """
    Create a single fallback NVDA B+ trade from the first data row of the CSV.

    Expected CSV schema (your demo file):
        timestamp,open,high,low,close,volume[,bplus_label]

    We derive:
        - date from timestamp (YYYY-MM-DD)
        - regime fixed as "NVDA_BPLUS_REPLAY"
        - entry_ts / exit_ts = timestamp (no offset)
        - gross_pnl_pct = 0.7
        - r_multiple    = 2.0
    """
    ts_value = "2025-10-17T06:30:00Z"
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            first = next(reader, None)
            if first and "timestamp" in first and first["timestamp"]:
                ts_value = first["timestamp"]
    except OSError:
        # Fall back to hard-coded timestamp if CSV read fails
        pass

    # Derive date (YYYY-MM-DD) from timestamp
    if "T" in ts_value:
        date_str = ts_value.split("T", 1)[0]
    else:
        date_str = "2025-10-17"

    basename = os.path.basename(csv_path)

    return {
        "date": date_str,
        "symbol": symbol,
        "regime": "NVDA_BPLUS_REPLAY",
        "entry_ts": ts_value,
        "exit_ts": ts_value,
        "gross_pnl_pct": 0.7,
        "r_multiple": 2.0,
        "pattern_tag": "NVDA_BPLUS_FALLBACK",
        "source_file": basename,
        "phase5_allowed": True,
        "phase5_reason": "fallback_no_trades",
        "phase5_gate": "fallback",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Loose NVDA B+ replay: call strict sim, then synthesize if empty."
    )
    parser.add_argument("--csv", required=True, help="Input NVDA CSV (OHLCV).")
    parser.add_argument("--symbol", required=True, help="Symbol, e.g. NVDA.")
    parser.add_argument("--out", required=True, help="Output JSONL path.")
    parser.add_argument("--tp", type=float, default=0.7, help="Take-profit pct.")
    parser.add_argument("--sl", type=float, default=0.35, help="Stop-loss pct.")

    args = parser.parse_args()

    # 1) Call the original strict simulator
    script_dir = os.path.dirname(os.path.abspath(__file__))
    strict_sim = os.path.join(script_dir, "sim_nvda_bplus_replay.py")

    cmd = [
        sys.executable,
        strict_sim,
        "--csv",
        args.csv,
        "--symbol",
        args.symbol,
        "--out",
        args.out,
        "--tp",
        str(args.tp),
        "--sl",
        str(args.sl),
    ]

    print(f"[LOOSE] Calling strict NVDA B+ sim: {' '.join(cmd)}")
    subprocess.run(cmd, check=False)

    # 2) Check output JSONL from strict sim
    out_path = args.out
    have_trades = False
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                for _ in f:
                    have_trades = True
                    break
        except OSError:
            have_trades = False

    if have_trades:
        print("[LOOSE] Strict sim produced trades; using them as-is.")
        return

    # 3) Strict sim produced NO trades -> synthesize one fallback record
    print("[LOOSE] Strict sim produced NO trades; synthesizing one fallback NVDA trade.")
    rec = synthesize_fallback_trade(args.csv, args.symbol)

    out_dir = os.path.dirname(out_path) or "."
    os.makedirs(out_dir, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f_out:
        f_out.write(json.dumps(rec) + "\\n")

    print(f"[LOOSE] Wrote 1 fallback trade to {os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()