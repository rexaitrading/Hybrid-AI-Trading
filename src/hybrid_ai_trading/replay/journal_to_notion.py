from __future__ import annotations

import argparse
import csv
from pathlib import Path

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--journal-csv', required=True, help='Path to logs\\replay_journal.csv')
    p.add_argument('--out-csv',     required=True, help='Path to write consolidated Notion CSV (e.g. logs\\replay_journal.snap.csv)')
    p.add_argument('--snapshots-dir', required=False, default='', help='Optional: path to snapshots for linking')
    p.add_argument('--window', type=int, default=60, help='kept for compatibility (not used yet)')
    args = p.parse_args()

    in_path  = Path(args.journal_csv)
    out_path = Path(args.out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not in_path.exists():
        raise SystemExit(f"Input journal not found: {in_path}")

    with in_path.open('r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        out_path.write_text('', encoding='utf-8')
        print(f"[journal2notion] input is empty: {in_path}")
        return

    fieldnames = list(rows[0].keys())
    # If you plan to attach screenshot paths later, you can add a column:
    # if 'screenshot_path' not in fieldnames:
    #     fieldnames.append('screenshot_path')

    with out_path.open('w', newline='', encoding='utf-8') as fo:
        writer = csv.DictWriter(fo, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            # Optionally attach screenshot link here if args.snapshots_dir is set and you have a naming convention
            writer.writerow(r)

    print(f"[journal2notion] wrote {out_path} with {len(rows)} rows")

if __name__ == '__main__':
    main()
