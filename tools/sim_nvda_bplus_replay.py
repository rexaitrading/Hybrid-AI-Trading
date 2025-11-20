"""
NVDA B+ replay-only simulator (Phase 4 / Option B)

- Long only
- Fixed TP = +0.7% from entry
- Fixed SL = -0.35% from entry
- One position at a time (no pyramiding)
- Offline research only (no live trading)

Enhancement:
- If CSV has bar-by-bar B+ label column (bplus_label OR pattern_tag),
  use that as the *exact* NVDA B+ signal (bar-by-bar match to your logs).
- If no labels are found, fall back to heuristic B+ detection.

Supported CSV schemas:

1) Full OHLCV (preferred):
   timestamp,open,high,low,close,volume[,bplus_label|pattern_tag]

2) Replay price-only (your current replay.csv):
   ts,symbol,price,volume
   (entry/exit logic uses price as open=high=low=close)
"""

import argparse
import csv
from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class Bar:
    ts: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    bplus_label: str = ""  # from your pattern logs, e.g. "B+"


@dataclass
class Trade:
    symbol: str
    side: str  # "long"
    entry_ts: str
    entry_price: float
    exit_ts: str
    exit_price: float
    tp_pct: float
    sl_pct: float
    outcome: str  # "TP", "SL", "EOD"
    r_multiple: float
    gross_pnl_pct: float
    bars_held: int
    mfe_pct: float
    mae_pct: float
    notes: str = ""


def load_bars(csv_path: str) -> List[Bar]:
    """
    Load bars from CSV, supporting two schemas:

    1) OHLCV:
       - columns: timestamp, open, high, low, close, [volume], [bplus_label], [pattern_tag]

    2) Replay price-only:
       - columns: ts, symbol, price, [volume]
       - we treat price as open=high=low=close
    """
    bars: List[Bar] = []
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = [name.lower() for name in (reader.fieldnames or [])]

        has_timestamp = "timestamp" in fieldnames
        has_ts = "ts" in fieldnames
        has_price = "price" in fieldnames
        has_open = "open" in fieldnames
        has_high = "high" in fieldnames
        has_low = "low" in fieldnames
        has_close = "close" in fieldnames

        # Basic schema detection
        if has_timestamp and has_open and has_high and has_low and has_close:
            schema = "ohlcv"
            print("[SIM] Detected OHLCV schema (timestamp,open,high,low,close...).")
        elif has_ts and has_price:
            schema = "ts_price"
            print("[SIM] Detected price-only replay schema (ts,price,...).")
        else:
            raise SystemExit(
                f"Unsupported CSV schema for {csv_path}. "
                f"Fieldnames: {reader.fieldnames}"
            )

        for row in reader:
            if schema == "ohlcv":
                # label from bplus_label or pattern_tag, if present
                lbl = ""
                if "bplus_label" in row:
                    lbl = str(row["bplus_label"] or "")
                elif "pattern_tag" in row:
                    lbl = str(row["pattern_tag"] or "")

                bar = Bar(
                    ts=str(row["timestamp"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume", 0.0)),
                    bplus_label=lbl,
                )
            else:
                # ts / price schema
                price = float(row["price"])
                vol_val = 0.0
                if "volume" in row and row["volume"] not in ("", None):
                    vol_val = float(row["volume"])

                # No pattern labels in this schema (replay.csv), so bplus_label=""
                bar = Bar(
                    ts=str(row["ts"]),
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=vol_val,
                    bplus_label="",
                )

            bars.append(bar)

    return bars


def rolling_median(values: List[float], window: int, idx: int) -> Optional[float]:
    if idx + 1 < window:
        return None
    slice_vals = values[idx + 1 - window : idx + 1]
    sorted_vals = sorted(slice_vals)
    n = len(sorted_vals)
    if n == 0:
        return None
    mid = n // 2
    if n % 2 == 1:
        return sorted_vals[mid]
    return 0.5 * (sorted_vals[mid - 1] + sorted_vals[mid])


def is_bplus_heuristic(
    bars: List[Bar],
    idx: int,
    roll_len_price: int = 10,
    roll_len_vol: int = 20,
    max_dist_from_mean_pct: float = 0.5,
) -> bool:
    """
    Approximate NVDA B+ setup (fallback when no labels exist):

    - We are not at the very start (need prior context).
    - Close is near rolling "VWAP-like" mean (using rolling close).
    - Current low is a higher low vs a recent swing low.
    - Volume > rolling median volume.
    """
    if idx < 2:
        return False

    closes = [b.close for b in bars]
    vols = [b.volume for b in bars]

    mean_close = rolling_median(closes, roll_len_price, idx)
    med_vol = rolling_median(vols, roll_len_vol, idx)

    if mean_close is None or med_vol is None:
        return False

    bar = bars[idx]
    # distance from mean in percent
    dist_pct = abs(bar.close - mean_close) / mean_close 
    if dist_pct > max_dist_from_mean_pct:
        return False

    # simple higher-low check vs prior 3-bars swing low
    recent_lows = [b.low for b in bars[idx - 3 : idx]]
    if len(recent_lows) < 3:
        return False
    prior_swing_low = min(recent_lows)
    if bar.low <= prior_swing_low:
        return False

    # volume above median
    if bar.volume <= med_vol:
        return False

    return True


def is_bplus_signal(
    bars: List[Bar],
    idx: int,
    use_labels: bool,
    roll_len_price: int = 10,
    roll_len_vol: int = 20,
    max_dist_from_mean_pct: float = 0.5,
) -> bool:
    """
    Combined signal:
    - If use_labels == True, fire when bplus_label/pattern_tag == "B+".
    - Otherwise, fall back to heuristic.
    """
    if use_labels:
        lbl = (bars[idx].bplus_label or "").strip().upper()
        if lbl == "B+":
            return True
        else:
            return False

    # No labels: use heuristic
    return is_bplus_heuristic(
        bars,
        idx,
        roll_len_price=roll_len_price,
        roll_len_vol=roll_len_vol,
        max_dist_from_mean_pct=max_dist_from_mean_pct,
    )


def simulate_trades(
    symbol: str,
    bars: List[Bar],
    tp_pct: float = 0.007,
    sl_pct: float = 0.0035,
) -> List[Trade]:
    """
    Long-only replay sim.

    - When is_bplus_signal() returns True on bar i, we enter at bar.close.
    - TP = entry_price * (1 + tp_pct/100).
    - SL = entry_price * (1 - sl_pct/100).
    - For each subsequent bar, if both TP and SL are within the same bar,
      we assume SL gets hit first (conservative assumption).
    - If neither TP nor SL is reached by the final bar, we exit at last close (EOD).
    """
    trades: List[Trade] = []

    # Detect whether we have at least one explicit label
    use_labels = any((b.bplus_label or "").strip() for b in bars)
    if use_labels:
        print("[SIM] Using bar-by-bar B+ labels from CSV (bplus_label/pattern_tag).")
    else:
        print("[SIM] No B+ labels detected; using heuristic B+ logic.")

    in_trade = False
    entry_idx = -1
    entry_price = 0.0
    tp_price = 0.0
    sl_price = 0.0

    mfe_pct = 0.0
    mae_pct = 0.0

    i = 0
    n = len(bars)
    while i < n:
        bar = bars[i]

        if not in_trade:
            if is_bplus_signal(bars, i, use_labels=use_labels):
                # Enter long at close
                entry_idx = i
                entry_price = bar.close
                tp_price = entry_price * (1.0 + tp_pct)
                sl_price = entry_price * (1.0 - sl_pct)
                in_trade = True
                mfe_pct = 0.0
                mae_pct = 0.0
            i += 1
            continue

        # In an open trade: update MFE/MAE based on this bar
        up_pct = (bar.high - entry_price) / entry_price 
        down_pct = (bar.low - entry_price) / entry_price 

        if up_pct > mfe_pct:
            mfe_pct = up_pct
        if down_pct < mae_pct:
            mae_pct = down_pct

        hit_tp = bar.high >= tp_price
        hit_sl = bar.low <= sl_price

        outcome = None
        exit_price = None
        exit_idx = None

        if hit_tp and hit_sl:
            # conservative: assume SL first
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

        if outcome is not None:
            exit_bar = bars[exit_idx]
            gross_pnl_pct = (exit_price - entry_price) / entry_price 
            r_multiple = gross_pnl_pct / sl_pct  # 1R = 0.35% for SL

            trade = Trade(
                symbol=symbol,
                side="long",
                entry_ts=bars[entry_idx].ts,
                entry_price=entry_price,
                exit_ts=exit_bar.ts,
                exit_price=exit_price,
                tp_pct=tp_pct,
                sl_pct=sl_pct,
                outcome=outcome,
                r_multiple=r_multiple,
                gross_pnl_pct=gross_pnl_pct,
                bars_held=exit_idx - entry_idx,
                mfe_pct=mfe_pct,
                mae_pct=mae_pct,
                notes="NVDA B+ replay (labels={} heuristic={})".format(
                    use_labels, not use_labels
                ),
            )
            trades.append(trade)

            in_trade = False
            entry_idx = -1
            entry_price = 0.0
            tp_price = 0.0
            sl_price = 0.0
            i += 1
            continue

        i += 1

    # If still in trade at end-of-data, close at final close
    if in_trade and entry_idx >= 0:
        last_bar = bars[-1]
        exit_price = last_bar.close
        gross_pnl_pct = (exit_price - entry_price) / entry_price 
        r_multiple = gross_pnl_pct / sl_pct

        trade = Trade(
            symbol=symbol,
            side="long",
            entry_ts=bars[entry_idx].ts,
            entry_price=entry_price,
            exit_ts=last_bar.ts,
            exit_price=exit_price,
            tp_pct=tp_pct,
            sl_pct=sl_pct,
            outcome="EOD",
            r_multiple=r_multiple,
            gross_pnl_pct=gross_pnl_pct,
            bars_held=len(bars) - 1 - entry_idx,
            mfe_pct=mfe_pct,
            mae_pct=mae_pct,
            notes="NVDA B+ replay EOD (labels={} heuristic={})".format(
                use_labels, not use_labels
            ),
        )
        trades.append(trade)

    return trades


def write_jsonl(trades: List[Trade], out_path: str) -> None:
    import json
    with open(out_path, "w", newline="") as f:
        for t in trades:
            f.write(json.dumps(asdict(t)) + "\n")


def summarize(trades: List[Trade]) -> None:
    if not trades:
        print("[SIM] No trades generated.")
        return

    wins = [t for t in trades if t.outcome == "TP"]
    losses = [t for t in trades if t.outcome == "SL"]
    eods = [t for t in trades if t.outcome == "EOD"]
    n = len(trades)

    avg_r = sum(t.r_multiple for t in trades) / float(n)
    avg_win_r = sum(t.r_multiple for t in wins) / float(len(wins)) if wins else 0.0
    avg_loss_r = sum(t.r_multiple for t in losses) / float(len(losses)) if losses else 0.0
    win_rate = 100.0 * len(wins) / float(n)

    print("[SIM] Trades:", n)
    print("[SIM] Wins (TP):", len(wins))
    print("[SIM] Losses (SL):", len(losses))
    print("[SIM] EOD exits:", len(eods))
    print("[SIM] Win rate: {:.2f}%".format(win_rate))
    print("[SIM] Avg R: {:.3f}".format(avg_r))
    print("[SIM] Avg Win R: {:.3f}".format(avg_win_r))
    print("[SIM] Avg Loss R: {:.3f}".format(avg_loss_r))


def main() -> None:
    parser = argparse.ArgumentParser(description="NVDA B+ replay sim (0.7% TP / 0.35% SL).")
    parser.add_argument("--csv", required=True, help="Path to NVDA OHLCV or replay CSV.")
    parser.add_argument("--symbol", default="NVDA", help="Symbol label for output.")
    parser.add_argument("--out", required=True, help="Output JSONL path.")
    parser.add_argument("--tp", type=float, default=0.7, help="TP in percent (default 0.7).")
    parser.add_argument("--sl", type=float, default=0.0035, help="SL in percent (default 0.35).")
    args = parser.parse_args()

    bars = load_bars(args.csv)
    if not bars:
        print("[SIM] No bars loaded from", args.csv)
        return

    trades = simulate_trades(symbol=args.symbol, bars=bars, tp_pct=args.tp, sl_pct=args.sl)
    write_jsonl(trades, args.out)
    summarize(trades)


if __name__ == "__main__":
    main()
