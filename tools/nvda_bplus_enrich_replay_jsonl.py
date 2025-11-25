#!/usr/bin/env python3
"""
NVDA B+ replay enricher (Phase-5 aware, glob-based).

- Scans an input directory for JSONL files matching a glob pattern
  (e.g. "nvda_bplus_replay_*.jsonl").
- Reads all records from those files.
- Ensures "source_file" is present for each record.
- Writes a single enriched JSONL file.

This is intentionally simple and robust: it does not depend on any
hard-coded filename regex. If a file matches the glob, it is used.
"""

import argparse
import glob
import json
import os
import sys
from typing import Any, Dict, Iterable, List


def iter_records(path: str) -> Iterable[Dict[str, Any]]:
    """Yield JSON objects from a JSONL file, skipping blanks/bad lines."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                print(
                    f"[nvda_bplus_enrich] WARNING: bad JSON line in {path}, skipping",
                    file=sys.stderr,
                )
                continue
            if isinstance(rec, dict):
                yield rec


def enrich_files(input_dir: str, pattern: str, output_path: str) -> None:
    """Aggregate/enrich all matching JSONL files into a single output."""
    # Expand glob pattern in the given directory
    glob_pattern = os.path.join(input_dir, pattern)
    files: List[str] = sorted(glob.glob(glob_pattern))

    if not files:
        print(
            f"[nvda_bplus_enrich] WARNING: no files matched pattern: {glob_pattern}",
            file=sys.stderr,
        )

    out_dir = os.path.dirname(output_path) or "."
    os.makedirs(out_dir, exist_ok=True)

    processed_files = 0
    input_lines = 0
    output_lines = 0

    with open(output_path, "w", encoding="utf-8") as f_out:
        for path in files:
            processed_files += 1
            basename = os.path.basename(path)
            for rec in iter_records(path):
                input_lines += 1
                # Ensure we always carry a "source_file" field
                rec.setdefault("source_file", basename)
                f_out.write(json.dumps(rec) + "\n")
                output_lines += 1

    print(f"[nvda_bplus_enrich] Processed files : {processed_files}")
    print(f"[nvda_bplus_enrich] Input lines     : {input_lines}")
    print(f"[nvda_bplus_enrich] Output lines    : {output_lines}")
    print(f"[nvda_bplus_enrich] Output JSONL    : {os.path.abspath(output_path)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich NVDA B+ replay JSONL files into a single Phase-5 JSONL."
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing replay JSONL files (e.g. replay_out).",
    )
    parser.add_argument(
        "--pattern",
        default="nvda_bplus_replay_*.jsonl",
        help='Glob pattern for replay files (default: "nvda_bplus_replay_*.jsonl")',
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to enriched JSONL output file.",
    )

    args = parser.parse_args()
    enrich_files(args.input_dir, args.pattern, args.output)


if __name__ == "__main__":
    main()