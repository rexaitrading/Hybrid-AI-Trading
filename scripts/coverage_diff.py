"""
Coverage Diff Helper
====================
Run this after pytest to see exactly which lines/branches are still uncovered.

Usage:
    python scripts/coverage_diff.py hybrid_ai_trading/signals/vwap.py
"""

import json
import subprocess
import sys
from pathlib import Path


def run_coverage_json():
    """Generate fresh coverage JSON file via pytest-cov if needed."""
    subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "json",
            "-o",
            "coverage.json",
        ],
        check=True,
    )


def load_coverage():
    path = Path("coverage.json")
    if not path.exists():
        run_coverage_json()
    with path.open() as f:
        return json.load(f)


def show_diff(target_file: str):
    data = load_coverage()
    files = data.get("files", {})
    abs_target = str(Path(target_file).resolve())

    # find matching file
    match = None
    for fname, meta in files.items():
        if fname.endswith(target_file) or str(fname).endswith(
            target_file.replace("\\", "/")
        ):
            match = (fname, meta)
            break

    if not match:
        print(f"Ã¢ÂÅ’ File {target_file} not found in coverage.json")
        return

    fname, meta = match
    summary = meta["summary"]
    missing = meta.get("missing_lines", [])
    branches = meta.get("missing_branches", [])

    print(f"\n=== Coverage Report for {fname} ===")
    print(
        f"Lines: {summary['covered_lines']}/{summary['num_statements']} "
        f"({summary['percent_covered']}%)"
    )
    print(f"Branches: {summary['covered_branches']}/{summary['num_branches']}")

    if missing:
        print("\nÃ¢ÂÅ’ Missing Lines:")
        print(", ".join(map(str, missing)))
    if branches:
        print("\nÃ¢ÂÅ’ Missing Branches:")
        for br in branches:
            print(f"  Line {br[0]} Ã¢â€ â€™ Branch {br[1]}")

    if not missing and not branches:
        print("\nÃ¢Å“â€¦ 100% Coverage!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/coverage_diff.py <path-to-file>")
        sys.exit(1)

    show_diff(sys.argv[1])
