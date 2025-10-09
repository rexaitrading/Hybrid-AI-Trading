"""
collect_cryptocompare.py
Continuous collector for CryptoCompare API with per-day quota enforcement.
"""

import csv
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from debug_cryptocompare import daily_budget  # must be defined in your helper
from debug_cryptocompare import fetch_prices  # must be defined in your helper
from debug_cryptocompare import (
    suggested_interval_seconds,  # must be defined in your helper
)

# === API Key Handling =====================================================
API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
if not API_KEY:
    raise EnvironmentError(
        "❌ CRYPTOCOMPARE_API_KEY is not set. "
        'Run: setx CRYPTOCOMPARE_API_KEY "your_key_here" '
        "and restart your terminal."
    )

# === Limits / Constants ===================================================
MONTHLY_CALLS = 11000
DATA_DIR = Path("data")


# -------------------------------------------------------------------------
def today_csv_path(base_dir: Path = DATA_DIR) -> Path:
    """Return today's (UTC) CSV path."""
    d = datetime.now(timezone.utc).strftime("%Y%m%d")
    return base_dir / f"cryptocompare_prices_{d}.csv"


def seconds_until_tomorrow_utc() -> int:
    """Return seconds until next UTC midnight + 10s buffer."""
    now = datetime.now(timezone.utc)
    midnight = datetime.combine(
        (now + timedelta(days=1)).date(),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    return max(1, int((midnight - now).total_seconds()) + 10)


def count_today_calls() -> int:
    """Count how many rows were already written today (UTC)."""
    path = today_csv_path()
    if not path.exists():
        return 0

    today = datetime.now(timezone.utc).date()
    count = 0
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = datetime.fromisoformat(row["timestamp"])
            if ts.date() == today:
                count += 1
    return count


def print_and_save(data: dict):
    """Save API results into today’s CSV with header management."""
    path = today_csv_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()

    ts = datetime.now(timezone.utc).isoformat()
    rows = [
        {"timestamp": ts, "symbol": sym, "usd": float(entry.get("USD"))}
        for sym, entry in (data or {}).items()
        if entry and entry.get("USD") is not None
    ]

    if not rows:
        print("⚠️ No rows to write")
        return

    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "symbol", "usd"])
        if new_file:
            writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Saved {len(rows)} rows -> {path}")


def loop_fetch(monthly_calls: int | None = None):
    """Main collector loop with per-day quota enforcement."""
    now = datetime.now(timezone.utc)
    year, month = now.year, now.month

    monthly = monthly_calls or MONTHLY_CALLS
    per_day = daily_budget(year, month, monthly)
    interval = suggested_interval_seconds(year, month, monthly)

    print(
        f"[collector] {year}-{month:02d} → target/day ≈ {per_day}, interval ≈ {interval}s"
    )

    while True:
        now = datetime.now(timezone.utc)
        if (now.year, now.month) != (year, month):
            year, month = now.year, now.month
            per_day = daily_budget(year, month, monthly)
            interval = suggested_interval_seconds(year, month, monthly)
            print(
                f"[rollover] Entered {year}-{month:02d}; new quota/day ≈ {per_day}, interval ≈ {interval}s"
            )

        used_today = count_today_calls()
        if used_today >= per_day:
            sleep_s = seconds_until_tomorrow_utc()
            print(
                f"[quota] Reached {used_today}/{per_day}, sleeping {sleep_s}s until UTC midnight…"
            )
            time.sleep(sleep_s)
            continue

        try:
            data = fetch_prices()
            print_and_save(data)
        except Exception as e:
            print("❌ Error fetching data:", e)

        time.sleep(interval)


if __name__ == "__main__":
    loop_fetch()
