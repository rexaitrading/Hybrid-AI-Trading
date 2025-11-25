"""
SPY ORB replay enricher.

- Scans replay_out/spy_orb_trades_*.jsonl
- Parses metadata out of the filename:
    spy_orb_trades_YYYYMMDD_orb5_tp2.5.jsonl
    -> day = YYYY-MM-DD
    -> orb_minutes = 5
    -> tp_pct = 2.5
- Adds these fields to each trade record:
    - day
    - orb_minutes
    - tp_pct
    - source_file
- Writes a merged enriched JSONL (default: research/spy_orb_replay_trades_enriched.jsonl)

This script is intentionally conservative:
- It does NOT assume any specific trade schema inside JSON lines.
- It simply passes through all existing keys and adds metadata.
"""

import argparse
import json
import os
import re
from pathlib import Path
from typing import Iterator, Dict, Any, Optional

FILENAME_RE = re.compile(
    r"""
    ^spy_orb_trades_
    (?P<day>\d{8})
    (?:_orb(?P<orb>\d+))?
    (?:_tp(?P<tp>[\d\.]+))?
    \.jsonl$
    """,
    re.VERBOSE,
)


def parse_filename_meta(path: Path) -> Optional[Dict[str, Any]]:
    """
    Parse metadata (day, orb_minutes, tp_pct) from a filename like:
      spy_orb_trades_20251110_orb5_tp2.5.jsonl
    If pieces are missing, we still return what we have.
    """
    m = FILENAME_RE.match(path.name)
    if not m:
        return None

    day_raw = m.group("day")
    day = f"{day_raw[0:4]}-{day_raw[4:6]}-{day_raw[6:8]}" if day_raw else None

    orb_raw = m.group("orb")
    orb_minutes = int(orb_raw) if orb_raw is not None else None

    tp_raw = m.group("tp")
    tp_pct = float(tp_raw) if tp_raw is not None else None

    return {
        "day": day,
        "orb_minutes": orb_minutes,
        "tp_pct": tp_pct,
    }


def iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # skip malformed lines but do not crash the entire script
                continue


def enrich_trades(input_dir: Path, pattern: str, output_path: Path) -> None:
    input_dir = input_dir.resolve()
    output_path = output_path.resolve()

    files = sorted(input_dir.glob(pattern))
    if not files:
        print(f"[spy_orb_enrich] No files matching pattern '{pattern}' under {input_dir}")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    count_files = 0
    count_lines_in = 0
    count_lines_out = 0

    with output_path.open("w", encoding="utf-8") as out_f:
        for file_path in files:
            meta = parse_filename_meta(file_path)
            if meta is None:
                print(f"[spy_orb_enrich] WARNING: filename did not match pattern, skipping: {file_path.name}")
                continue

            count_files += 1
            for record in iter_jsonl(file_path):
                count_lines_in += 1
                enriched = dict(record)
                # Attach metadata
                enriched.setdefault("day", meta["day"])
                enriched.setdefault("orb_minutes", meta["orb_minutes"])
                enriched.setdefault("tp_pct", meta["tp_pct"])
                enriched.setdefault("source_file", file_path.name)

                out_f.write(json.dumps(enriched, ensure_ascii=False) + "\n")
                count_lines_out += 1

    print(f"[spy_orb_enrich] Processed files : {count_files}")
    print(f"[spy_orb_enrich] Input lines     : {count_lines_in}")
    print(f"[spy_orb_enrich] Output lines    : {count_lines_out}")
    print(f"[spy_orb_enrich] Output JSONL    : {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="SPY ORB replay trades enricher")
    parser.add_argument(
        "--input-dir",
        default="replay_out",
        help="Directory containing spy_orb_trades_*.jsonl (default: replay_out)",
    )
    parser.add_argument(
        "--pattern",
        default="spy_orb_trades_*.jsonl",
        help="Glob pattern for input files (default: spy_orb_trades_*.jsonl)",
    )
    parser.add_argument(
        "--output",
        default="research/spy_orb_replay_trades_enriched.jsonl",
        help="Output JSONL path (default: research/spy_orb_replay_trades_enriched.jsonl)",
    )

    args = parser.parse_args()
    input_dir = Path(args.input_dir)
    output_path = Path(args.output)

    enrich_trades(input_dir=input_dir, pattern=args.pattern, output_path=output_path)


if __name__ == "__main__":
    main()