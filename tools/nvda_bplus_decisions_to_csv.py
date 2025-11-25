#!/usr/bin/env python3
"""
NVDA B+ decisions -> CSV for Notion (Phase-5 aware).

Reads enriched NVDA B+ replay JSONL and writes a flat CSV suitable
for Notion dashboards.

- Default input:  research/nvda_bplus_replay_enriched.jsonl
- Default output: logs/nvda_bplus_trades_for_notion.csv

Fieldnames include Phase-5 gating columns (phase5_*). If a field is
missing in the JSON, it is left blank in the CSV.
"""

import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, Iterable, List

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
    # Phase-5 gating fields (may be missing in some JSON records)
    "phase5_allowed",
    "phase5_reason",
    "phase5_gate",
]


def iter_records(path: str) -> Iterable[Dict[str, Any]]:
    """Yield JSON objects from a JSONL file (skip blank/invalid lines)."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                # Skip malformed lines rather than crashing the exporter
                continue
            if isinstance(rec, dict):
                yield rec


def record_to_row(rec: Dict[str, Any]) -> Dict[str, str]:
    """
    Map a JSON record to a flat CSV row with all FIELDNAMES.

    - Missing keys -> empty string
    - Booleans -> "true"/"false" (lowercase), suitable for Notion checkboxes
    """
    row: Dict[str, str] = {}
    for key in FIELDNAMES:
        value = rec.get(key, "")

        if isinstance(value, bool):
            row[key] = "true" if value else "false"
        elif value is None:
            row[key] = ""
        else:
            row[key] = str(value)

    return row


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export NVDA B+ decisions (Phase-5 aware) to CSV for Notion."
    )
    parser.add_argument(
        "--input",
        default="research/nvda_bplus_replay_enriched.jsonl",
        help="Input JSONL file (default: research/nvda_bplus_replay_enriched.jsonl)",
    )
    parser.add_argument(
        "--output",
        default="logs/nvda_bplus_trades_for_notion.csv",
        help="Output CSV file (default: logs/nvda_bplus_trades_for_notion.csv)",
    )

    args = parser.parse_args()
    input_path = args.input
    output_path = args.output

    if not os.path.exists(input_path):
        print(f"[ERROR] Input JSONL not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = os.path.dirname(output_path) or "."
    os.makedirs(out_dir, exist_ok=True)

    wrote_any = False

    with open(output_path, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=FIELDNAMES)
        writer.writeheader()

        for rec in iter_records(input_path):
            row = record_to_row(rec)
            writer.writerow(row)
            wrote_any = True

    if wrote_any:
        print(f"[OK] Wrote NVDA B+ CSV with Phase-5 columns: {output_path}")
    else:
        print(
            f"[OK] Wrote NVDA B+ CSV header only (no records) with Phase-5 columns: {output_path}"
        )


if __name__ == "__main__":
    main()