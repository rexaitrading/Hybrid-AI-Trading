"""
Convert SPY ORB enriched replay trades JSONL to a CSV suitable for Notion import.

Input:
  research/spy_orb_replay_trades_enriched.jsonl

Output:
  logs/spy_phase5_trades_for_notion.csv
"""

import csv
import json
from pathlib import Path
from datetime import datetime


def main() -> None:
    src = Path("research/spy_orb_replay_trades_enriched.jsonl")
    dst = Path("logs/spy_phase5_trades_for_notion.csv")

    print(f"[spy_orb_to_csv] Input : {src}")
    print(f"[spy_orb_to_csv] Output: {dst}")

    if not src.exists():
        print(f"[spy_orb_to_csv] Input not found: {src}")
        return

    dst.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "date",
        "symbol",
        "regime",
        "entry_ts",
        "exit_ts",
        "gross_pnl_pct",
        "r_multiple",
        "orb_minutes",
        "tp_pct",
        "source_file",
    ]

    written = 0

    with src.open("r", encoding="utf-8") as f_in, dst.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for line in f_in:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_ts = rec.get("entry_ts")
            date_str = ""
            if isinstance(entry_ts, str):
                try:
                    dt = datetime.fromisoformat(entry_ts.replace("Z", "+00:00"))
                    date_str = dt.date().isoformat()
                except Exception:
                    date_str = ""

            row = {
                "date": date_str or rec.get("day") or "",
                "symbol": rec.get("symbol", "SPY"),
                "regime": rec.get("regime", "SPY_ORB_REPLAY"),
                "entry_ts": entry_ts or "",
                "exit_ts": rec.get("exit_ts", ""),
                "gross_pnl_pct": rec.get("gross_pnl_pct", ""),
                "r_multiple": rec.get("r_multiple", ""),
                "orb_minutes": rec.get("orb_minutes", ""),
                "tp_pct": rec.get("tp_pct", ""),
                "source_file": rec.get("source_file", ""),
            }

            writer.writerow(row)
            written += 1

    print(f"[spy_orb_to_csv] Wrote {written} rows to {dst}")
if __name__ == "__main__":
    main()