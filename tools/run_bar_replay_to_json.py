from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Minimal bar replay stub -> EV summary JSON"
    )

    # New-style flags
    parser.add_argument("--symbol", "-s", dest="symbol", help="Symbol (e.g. NVDA)")
    parser.add_argument("--csv", "-c", dest="csv_path", help="Path to input CSV")
    parser.add_argument("--session", "-n", dest="session", help="Session tag")
    parser.add_argument("--outdir", "-o", dest="outdir", default=".", help="Output directory")

    # Legacy flags from older PowerShell runner
    parser.add_argument("-symbol", dest="symbol", help="Symbol (legacy flag)")
    parser.add_argument("-csvPath", dest="csv_path", help="CSV path (legacy flag)")
    parser.add_argument("-session", dest="session", help="Session tag (legacy flag)")
    parser.add_argument("-outdir", dest="outdir", help="Output directory (legacy flag)")

    # Positional fallback: symbol csv_path session
    parser.add_argument("pos_symbol", nargs="?", help="Fallback symbol")
    parser.add_argument("pos_csv_path", nargs="?", help="Fallback CSV path")
    parser.add_argument("pos_session", nargs="?", help="Fallback session tag")

    args, _unknown = parser.parse_known_args()

    # Fallback to positionals if explicit flags missing
    if not args.symbol and args.pos_symbol:
        args.symbol = args.pos_symbol

    if not args.csv_path and args.pos_csv_path:
        args.csv_path = args.pos_csv_path

    if not args.session and args.pos_session:
        args.session = args.pos_session

    return args


def simple_replay_stats(csv_path: Path) -> Tuple[int, float]:
    """
    Minimal stub: count bars and return (count, dummy_ev_mean).
    """
    count = 0
    with csv_path.open(newline="") as f:
        reader = csv.reader(f)
        _header = next(reader, None)
        for _row in reader:
            count += 1

    # v1 stub: EV is zero; later versions can compute real EV
    ev_mean = 0.0
    return count, ev_mean


def main() -> None:
    args = parse_args()

    symbol = (args.symbol or "NVDA").upper()

    # If CSV path is still missing, try to infer from repo layout: data/<SYMBOL>_1m.csv
    if not args.csv_path:
        # Assume this script lives under repo_root/tools
        script_path = Path(__file__).resolve()
        repo_root = script_path.parents[1]
        guessed_csv = repo_root / "data" / f"{symbol}_1m.csv"
        if guessed_csv.is_file():
            args.csv_path = str(guessed_csv)
        else:
            raise SystemExit(
                f"CSV path must be provided via --csv / -csvPath / positional "
                f"and could not infer default for symbol={symbol}"
            )

    csv_path = Path(args.csv_path)
    if not csv_path.is_file():
        raise SystemExit(f"CSV not found: {csv_path}")

    session = args.session or "DEFAULT"

    # Resolve outdir relative to script location if needed
    outdir = Path(args.outdir or ".")
    if not outdir.is_absolute():
        script_path = Path(__file__).resolve()
        repo_root = script_path.parents[1]
        outdir = (repo_root / outdir).resolve()

    outdir.mkdir(parents=True, exist_ok=True)

    bars, ev_mean = simple_replay_stats(csv_path)

    summary = {
        "symbol": symbol,
        "session": session,
        "bars": bars,
        "ev": {
            "mean": ev_mean,
            "stdev": 0.0,
        },
    }

    out_path = outdir / f"replay_summary_{symbol}_{session}.json"
    out_path.write_text(json.dumps(summary, indent=2))

    # IMPORTANT: avoid printing full path with non-ASCII (e.g. 文件) to keep cp1252 consoles happy
    print(f"[REPLAY] Wrote summary file {out_path.name}")


if __name__ == "__main__":
    main()