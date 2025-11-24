"""
Simple QQQ ORB (Opening Range Breakout) simulator for 1-minute OHLCV data.

CSV schema (expected):

    timestamp,open,high,low,close,volume

We simulate at most one long trade per day:

- Session: RTH (09:30 - 16:00).
- ORB window: first N minutes of RTH (via orb_minutes).
- ORB high/low = max/min of that window.
- Entry: first bar after ORB window where high >= ORB high.
  - Enter long at bar.close.
- Risk per share = entry_price - ORB_low. If <= 0 -> skip trade.
- SL = ORB_low (approx -1R).
- TP = entry_price + tp_r * risk_per_share.
- If both TP and SL hit in same bar, SL is assumed first.
- If still open at end of session, exit at last close (EOD).
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, asdict
from datetime import datetime, time
from typing import List, Optional


@dataclass
class Bar:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Trade:
    symbol: str
    side: str  # "long"
    entry_ts: str
    entry_price: float
    exit_ts: str
    exit_price: float
    orb_high: float
    orb_low: float
    tp_price: float
    sl_price: float
    outcome: str  # "TP", "SL", "EOD"
    r_multiple: float
    gross_pnl_pct: float
    bars_held: int
    session: str
    regime: str


RTH_START = time(9, 30)
RTH_END = time(16, 0)


def parse_timestamp(ts_str: str) -> datetime:
    try:
        return datetime.fromisoformat(ts_str)
    except Exception:
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")


def load_bars_for_date(csv_path: str, date_str: str) -> List[Bar]:
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    bars: List[Bar] = []
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts_raw = row.get("timestamp") or row.get("ts")
            if not ts_raw:
                continue
            dt = parse_timestamp(str(ts_raw))
            if dt.date() != target_date:
                continue
            ttime = dt.time()
            if not (RTH_START <= ttime <= RTH_END):
                continue
            try:
                bar = Bar(
                    ts=dt,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume", 0.0)),
                )
            except Exception:
                continue
            bars.append(bar)
    bars.sort(key=lambda b: b.ts)
    return bars


def simulate_orb_for_day(
    symbol: str,
    bars: List[Bar],
    orb_minutes: int = 5,
    tp_r: float = 2.5,
) -> List[Trade]:
    trades: List[Trade] = []

    if not bars:
        return trades

    orb_window_bars = []
    for b in bars:
        if len(orb_window_bars) < orb_minutes:
            orb_window_bars.append(b)
        else:
            break

    if len(orb_window_bars) < orb_minutes:
        return trades

    orb_high = max(b.high for b in orb_window_bars)
    orb_low = min(b.low for b in orb_window_bars)

    in_trade = False
    entry_idx: Optional[int] = None
    entry_price = 0.0
    sl_price = 0.0
    tp_price = 0.0

    for i in range(len(orb_window_bars), len(bars)):
        bar = bars[i]

        if not in_trade:
            if bar.high >= orb_high:
                entry_idx = i
                entry_price = bar.close
                risk_per_share = entry_price - orb_low
                if risk_per_share <= 0:
                    entry_idx = None
                    entry_price = 0.0
                    continue
                sl_price = orb_low
                tp_price = entry_price + tp_r * risk_per_share
                in_trade = True
            continue

        high = bar.high
        low = bar.low

        hit_tp = high >= tp_price
        hit_sl = low <= sl_price

        outcome: Optional[str] = None
        exit_price: Optional[float] = None
        exit_idx: Optional[int] = None

        if hit_tp and hit_sl:
            outcome = "SL"
            exit_price = sl_price
            exit_idx = i
        elif hit_sl:
            outcome = "SL"
            exit_price = sl_price
            exit_idx = i
        elif hit_tp:
            outcome = "TP"
            exit_price = tp_price
            exit_idx = i

        if outcome is not None and entry_idx is not None:
            entry_bar = bars[entry_idx]
            exit_bar = bars[exit_idx]
            gross_pnl_pct = (exit_price - entry_price) / entry_price
            risk_per_share = entry_price - orb_low
            r_multiple = (exit_price - entry_price) / risk_per_share if risk_per_share > 0 else 0.0

            trade = Trade(
                symbol=symbol,
                side="long",
                entry_ts=entry_bar.ts.isoformat(),
                entry_price=entry_price,
                exit_ts=exit_bar.ts.isoformat(),
                exit_price=exit_price,
                orb_high=orb_high,
                orb_low=orb_low,
                tp_price=tp_price,
                sl_price=sl_price,
                outcome=outcome,
                r_multiple=r_multiple,
                gross_pnl_pct=gross_pnl_pct,
                bars_held=exit_idx - entry_idx,
                session="RTH",
                regime="QQQ_ORB_REPLAY",
            )
            trades.append(trade)
            in_trade = False
            break

    if in_trade and entry_idx is not None:
        entry_bar = bars[entry_idx]
        last_bar = bars[-1]
        exit_price = last_bar.close
        gross_pnl_pct = (exit_price - entry_price) / entry_price
        risk_per_share = entry_price - orb_low
        r_multiple = (exit_price - entry_price) / risk_per_share if risk_per_share > 0 else 0.0

        trade = Trade(
            symbol=symbol,
            side="long",
            entry_ts=entry_bar.ts.isoformat(),
            entry_price=entry_price,
            exit_ts=last_bar.ts.isoformat(),
            exit_price=exit_price,
            orb_high=orb_high,
            orb_low=orb_low,
            tp_price=tp_price,
            sl_price=sl_price,
            outcome="EOD",
            r_multiple=r_multiple,
            gross_pnl_pct=gross_pnl_pct,
            bars_held=len(bars) - 1 - entry_idx,
            session="RTH",
            regime="QQQ_ORB_REPLAY",
        )
        trades.append(trade)

    return trades


def write_jsonl(trades: List[Trade], out_path: str) -> None:
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        for t in trades:
            f.write(json.dumps(asdict(t)))
            f.write("\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="QQQ ORB 1m simulator (JSONL trades).")
    ap.add_argument("--csv", required=True, help="Path to QQQ 1m OHLCV CSV.")
    ap.add_argument("--date", required=True, help="Trading date (YYYY-MM-DD).")
    ap.add_argument("--symbol", default="QQQ", help="Symbol label (default QQQ).")
    ap.add_argument("--out", required=True, help="Output JSONL path.")
    ap.add_argument("--orb-minutes", type=int, default=5, help="ORB window length in minutes (default 5).")
    ap.add_argument("--tp-r", type=float, default=2.5, help="Take-profit in R multiples (default 2.5).")
    args = ap.parse_args()

    bars = load_bars_for_date(args.csv, args.date)
    if not bars:
        print(f"[QQQ_ORB] No bars found for date {args.date} in {args.csv}")
        write_jsonl([], args.out)
        return

    trades = simulate_orb_for_day(
        symbol=args.symbol,
        bars=bars,
        orb_minutes=args.orb_minutes,
        tp_r=args.tp_r,
    )
    write_jsonl(trades, args.out)
    print(f"[QQQ_ORB] Wrote {len(trades)} trades to {args.out}")


if __name__ == "__main__":
    main()