"""
Convert QQQ ORB enriched JSONL → CSV for Notion.

Input:
  research/qqq_orb_replay_trades_enriched.jsonl

Output:
  logs/qqq_phase5_trades_for_notion.csv
"""

import csv, json
from pathlib import Path
from datetime import datetime

def main():
    src = Path("research/qqq_orb_replay_trades_enriched.jsonl")
    dst = Path("logs/qqq_phase5_trades_for_notion.csv")
    print(f"[qqq_orb_to_csv] Input:  {src}")
    print(f"[qqq_orb_to_csv] Output: {dst}")

    if not src.exists():
        print(f"[qqq_orb_to_csv] Input not found.")
        return

    dst.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "date","symbol","regime","entry_ts","exit_ts",
        "gross_pnl_pct","r_multiple","orb_minutes","tp_pct","source_file"
    ]

    written = 0

    with src.open("r",encoding="utf-8") as f_in, \
         dst.open("w",newline="",encoding="utf-8") as f_out:

        wr = csv.DictWriter(f_out, fieldnames=fieldnames)
        wr.writeheader()

        for line in f_in:
            line=line.strip()
            if not line: continue
            try:
                rec=json.loads(line)
            except: continue

            entry_ts = rec.get("entry_ts")
            date=""
            if isinstance(entry_ts,str):
                try:
                    dt=datetime.fromisoformat(entry_ts.replace("Z","+00:00"))
                    date=dt.date().isoformat()
                except: pass

            wr.writerow({
                "date": date or rec.get("day") or "",
                "symbol": rec.get("symbol","QQQ"),
                "regime": rec.get("regime","QQQ_ORB_REPLAY"),
                "entry_ts": entry_ts or "",
                "exit_ts": rec.get("exit_ts",""),
                "gross_pnl_pct": rec.get("gross_pnl_pct",""),
                "r_multiple": rec.get("r_multiple",""),
                "orb_minutes": rec.get("orb_minutes",""),
                "tp_pct": rec.get("tp_pct",""),
                "source_file": rec.get("source_file",""),
            })
            written += 1

    print(f"[qqq_orb_to_csv] Wrote {written} rows → {dst}")

if __name__=="__main__":
    main()