#!/usr/bin/env python3
"""
Phase-5 CSV schema upgrader.

Takes an input CSV (e.g. SPY/QQQ Phase5 trades) and writes an output CSV
with the unified Phase-5 schema:

    date,symbol,regime,entry_ts,exit_ts,gross_pnl_pct,r_multiple,
    pattern_tag,source_file,phase5_allowed,phase5_reason,phase5_gate

Missing fields are filled with reasonable defaults or left blank.
"""

import argparse
import csv
from typing import Dict, List

FIELDNAMES: List[str] = [
    "date",
    "symbol",
    "regime",
    "entry_ts",
    "exit_ts",
    "gross_pnl_pct",
    "r_multiple",
    "pattern_tag",
    "source_file",
    "phase5_allowed",
    "phase5_reason",
    "phase5_gate",
]


def row_to_phase5(row: Dict[str, str]) -> Dict[str, str]:
    """Map an arbitrary input row into the unified Phase-5 schema."""
    out: Dict[str, str] = {}

    # Core fields (common across your CSVs)
    out["date"] = row.get("date", "")
    out["symbol"] = row.get("symbol", "")
    out["regime"] = row.get("regime", "")
    out["entry_ts"] = row.get("entry_ts", "")
    out["exit_ts"] = row.get("exit_ts", "")
    out["gross_pnl_pct"] = row.get("gross_pnl_pct", "")
    out["r_multiple"] = row.get("r_multiple", "")

    # pattern_tag: prefer existing, else fall back to regime
    pattern_tag = row.get("pattern_tag")
    if not pattern_tag:
        pattern_tag = row.get("regime", "")
    out["pattern_tag"] = pattern_tag or ""

    # source_file: prefer existing
    out["source_file"] = row.get("source_file", "")

    # Phase-5 fields: use existing if present, else blank
    phase5_allowed = row.get("phase5_allowed", "")
    if isinstance(phase5_allowed, bool):
        phase5_allowed_str = "true" if phase5_allowed else "false"
    else:
        phase5_allowed_str = str(phase5_allowed).lower() if phase5_allowed else ""
    out["phase5_allowed"] = phase5_allowed_str

    out["phase5_reason"] = row.get("phase5_reason", "")
    out["phase5_gate"] = row.get("phase5_gate", "")

    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upgrade a trades CSV to unified Phase-5 schema."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input CSV path.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output CSV path (Phase-5 schema).",
    )

    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8", newline="") as f_in, open(
        args.output, "w", encoding="utf-8", newline=""
    ) as f_out:
        reader = csv.DictReader(f_in)
        writer = csv.DictWriter(f_out, fieldnames=FIELDNAMES)
        writer.writeheader()

        wrote_any = False
        for row in reader:
            mapped = row_to_phase5(row)
            writer.writerow(mapped)
            wrote_any = True

    if wrote_any:
        print(f"[PHASE5_UPGRADE] Wrote Phase-5 CSV: {args.output}")
    else:
        print(f"[PHASE5_UPGRADE] Input had no data rows; wrote header only: {args.output}")


if __name__ == "__main__":
    main()