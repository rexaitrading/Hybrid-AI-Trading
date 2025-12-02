from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple


CSV_MAP = {
    "NVDA": ("logs/nvda_phase5_paper_for_notion.csv", "NVDA_BPLUS_LIVE"),
    "SPY":  ("logs/spy_phase5_paper_for_notion.csv",  "SPY_ORB_LIVE"),
    "QQQ":  ("logs/qqq_phase5_paper_for_notion.csv",  "QQQ_ORB_LIVE"),
}


def _read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        print(f"[WARN] CSV not found: {path}")
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _parse_float(d: Dict[str, str], key: str) -> Optional[float]:
    v = d.get(key)
    if v is None or v == "":
        return None
    try:
        return float(v)
    except Exception:
        return None


def _compute_stats(rows: List[Dict[str, str]]) -> Tuple[int, Optional[float], Optional[float], Optional[float]]:
    """
    Returns:
        n_trades, mean_ev, mean_realized_pct, stdev_realized_pct
    """
    ev_vals: List[float] = []
    realized_pct_vals: List[float] = []

    for r in rows:
        ev = _parse_float(r, "ev")
        if ev is not None:
            ev_vals.append(ev)

        # realized_pnl may be in realized_pnl or realized_pnl_paper
        rp = _parse_float(r, "realized_pnl")
        if rp is None:
            rp = _parse_float(r, "realized_pnl_paper")

        # notional if present, else qty * price
        notional = _parse_float(r, "notional")
        if notional is None:
            qty = _parse_float(r, "qty")
            price = _parse_float(r, "price")
            if qty is not None and price is not None:
                notional = qty * price

        if rp is not None and notional is not None and notional != 0.0:
            realized_pct_vals.append(rp / notional)

    n_trades = len(realized_pct_vals)
    if n_trades == 0:
        return 0, None, None, None

    def mean(xs: List[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    def stdev(xs: List[float]) -> float:
        if len(xs) < 2:
            return 0.0
        m = mean(xs)
        sq = sum((x - m) ** 2 for x in xs)
        return (sq / (len(xs) - 1)) ** 0.5

    mean_ev = mean(ev_vals) if ev_vals else None
    mean_realized = mean(realized_pct_vals)
    std_realized = stdev(realized_pct_vals)

    return n_trades, mean_ev, mean_realized, std_realized


def analyze_symbol(symbol: str, csv_path: str, regime: str) -> None:
    path = Path(csv_path)
    rows = _read_csv(path)
    if not rows:
        print(f"\n[EV-TUNE] {symbol} ({regime}): no rows in CSV")
        return

    # Filter to LIVE + SELL rows for the given regime
    live_rows: List[Dict[str, str]] = []
    for r in rows:
        if r.get("regime") != regime:
            continue
        if r.get("side", "").upper() != "SELL":
            continue

        origin = r.get("origin")
        if origin is not None and origin != "LIVE":
            continue

        live_rows.append(r)

    if not live_rows:
        print(f"\n[EV-TUNE] {symbol} ({regime}): no SELL LIVE rows")
        return

    n, mean_ev, mean_realized, std_realized = _compute_stats(live_rows)

    print(f"\n[EV-TUNE] {symbol} ({regime})")
    print(f"  SELL LIVE trades analyzed : {n}")
    if mean_ev is not None:
        print(f"  Mean EV (from CSV)       : {mean_ev:.6f}")
    else:
        print(f"  Mean EV (from CSV)       : <none>")

    if mean_realized is not None:
        print(f"  Mean realized pct        : {mean_realized:.6f}")
    else:
        print(f"  Mean realized pct        : <none>")

    if mean_ev is not None and mean_realized is not None:
        diff = mean_realized - mean_ev
        print(f"  Realized - EV            : {diff:.6f}")

    if std_realized is not None:
        print(f"  Realized pct stdev       : {std_realized:.6f}")

    # Heuristic band suggestions
    if mean_ev is not None:
        band_075 = 0.75 * abs(mean_ev)
        print(f"  Suggested band (0.75*EV) : {band_075:.6f}")

    if std_realized is not None and std_realized > 0:
        band_05std = 0.50 * std_realized
        print(f"  Suggested band (0.5*std) : {band_05std:.6f}")


def main() -> None:
    print("[EV-TUNE] Live EV tuning from CSV for NVDA / SPY / QQQ")
    for symbol, (csv_path, regime) in CSV_MAP.items():
        analyze_symbol(symbol, csv_path, regime)


if __name__ == "__main__":
    main()