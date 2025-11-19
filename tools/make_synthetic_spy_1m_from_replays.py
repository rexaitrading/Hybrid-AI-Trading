from __future__ import annotations

import glob
import json
import os
from datetime import datetime, timedelta, timezone

import pandas as pd  # type: ignore[import]


def make_spy_bars_from_replays(pattern: str, out_csv: str) -> None:
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"[SPY-SYN] No files matched pattern: {pattern}")
        return

    rows = []

    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            summary = json.load(f)

        session_open_str = summary.get("session_open")
        if not session_open_str:
            continue

        # Parse session_open, assume UTC
        session_open = datetime.fromisoformat(session_open_str.replace("Z", "+00:00"))
        date = session_open.date()

        # Create 1m bars from 14:30 to 20:00
        start = datetime(date.year, date.month, date.day, 14, 30, tzinfo=timezone.utc)
        end = datetime(date.year, date.month, date.day, 20, 0, tzinfo=timezone.utc)

        ts = start
        price = 500.0  # arbitrary base
        while ts <= end:
            # simple synthetic: small drift up
            price_open = price
            price_close = price + 0.1
            row = {
                "timestamp": ts.isoformat().replace("+00:00", "Z"),
                "open": price_open,
                "high": max(price_open, price_close),
                "low": min(price_open, price_close),
                "close": price_close,
                "volume": 1000,
            }
            rows.append(row)
            price = price_close
            ts += timedelta(minutes=1)

    if not rows:
        print("[SPY-SYN] No rows generated.")
        return

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False)
    print(f"[SPY-SYN] Wrote synthetic SPY bars to {out_csv} ({len(df)} rows)")


def main() -> None:
    pattern = "orb_vwap_replay_summary_SPY_*.json"
    out_csv = os.path.join("data", "SPY_1m.csv")
    make_spy_bars_from_replays(pattern, out_csv)


if __name__ == "__main__":
    main()