from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Tuple, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bar replay stub -> EV summary JSON with richer stats"
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


def _load_closes(csv_path: Path) -> Tuple[int, List[float]]:
    closes: List[float] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                close = float(row["close"])
            except Exception:
                continue
            closes.append(close)
    return len(closes), closes


def _compute_return_stats(closes: List[float]) -> Tuple[float, float, float, float, float, float]:
    """
    Compute:
      - mean_edge_ratio (we'll use mean return for now)
      - max_drawdown_pct
      - win_rate
      - avg_win
      - avg_loss
      - stdev of returns (for ev.stdev)
    """
    import math

    n = len(closes)
    if n < 2:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    rets: List[float] = []
    prev = closes[0]
    for c in closes[1:]:
        if prev != 0.0:
            rets.append((c - prev) / prev)
        prev = c

    if not rets:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    mean_r = sum(rets) / len(rets)

    # max drawdown from close series
    peak = closes[0]
    max_dd = 0.0
    for c in closes:
        if c > peak:
            peak = c
        if peak != 0.0:
            dd = (c - peak) / peak
            if dd < max_dd:
                max_dd = dd

    wins = [r for r in rets if r > 0.0]
    losses = [r for r in rets if r < 0.0]

    win_rate = len(wins) / len(rets) if rets else 0.0
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0

    # simple stdev of returns
    var = sum((r - mean_r) ** 2 for r in rets) / len(rets)
    stdev = math.sqrt(var)

    # For now, treat mean_edge_ratio as mean return
    mean_edge_ratio = mean_r

    max_drawdown_pct = max_dd  # negative value
    return mean_edge_ratio, max_drawdown_pct, win_rate, avg_win, avg_loss, stdev


def simple_replay_stats(csv_path: Path) -> Tuple[int, float, float, float, float, float, float, float]:
    """
    Compute richer stats from a simple OHLCV CSV:
      - bars
      - mean_edge_ratio
      - max_drawdown_pct
      - win_rate
      - avg_win
      - avg_loss
      - ev_mean
      - ev_stdev
    """
    n_bars, closes = _load_closes(csv_path)
    mean_edge_ratio, max_dd, win_rate, avg_win, avg_loss, stdev = _compute_return_stats(closes)
    ev_mean = mean_edge_ratio
    ev_stdev = stdev
    return n_bars, mean_edge_ratio, max_dd, win_rate, avg_win, avg_loss, ev_mean, ev_stdev


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

    (
        bars,
        mean_edge_ratio,
        max_drawdown_pct,
        win_rate,
        avg_win,
        avg_loss,
        ev_mean,
        ev_stdev,
    ) = simple_replay_stats(csv_path)

    summary = {
        "symbol": symbol,
        "session": session,
        "bars": bars,
        "mean_edge_ratio": mean_edge_ratio,
        "max_drawdown_pct": max_drawdown_pct,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "ev": {
            "mean": ev_mean,
            "stdev": ev_stdev,
        },
    }

    out_path = outdir / f"replay_summary_{symbol}_{session}.json"
    out_path.write_text(json.dumps(summary, indent=2))

    # IMPORTANT: avoid printing full path with non-ASCII (e.g. 文件) to keep cp1252 consoles happy
    print(f"[REPLAY] Wrote summary file {out_path.name}")


if __name__ == "__main__":
    main()
