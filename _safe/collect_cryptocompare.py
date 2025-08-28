# collect_cryptocompare.py
import os
import time
import csv
import calendar
from pathlib import Path
from datetime import datetime, timezone, timedelta

API_KEY = os.getenv('CRYPTOCOMPARE_API_KEY')
MONTHLY_CALLS = 11000

from debug_cryptocompare import (
    fetch_prices,
    print_and_save,
    daily_budget,
    suggested_interval_seconds,
)

DATA_PATH = Path("data/cryptocompare_prices.csv")

def today_csv_path(base_dir: Path = Path("data")) -> Path:
    """å›žå‚³ä»Šå¤©ï¼ˆUTCï¼‰å°æ‡‰çš„æ¯æ—¥æª”å"""
    d = datetime.now(timezone.utc).strftime("%Y%m%d")
    return base_dir / f"cryptocompare_prices_{d}.csv"


def seconds_until_tomorrow_utc() -> int:
    """å›žå‚³è·é›¢ UTC æ˜Žå¤© 00:00 çš„ç§’æ•¸ï¼Œå¤šåŠ  10 ç§’ç·©è¡ã€‚"""
    now = datetime.now(timezone.utc)
    midnight_tomorrow = datetime.combine(
        (now + timedelta(days=1)).date(), datetime.min.time(), tzinfo=timezone.utc
    )
    return max(1, int((midnight_tomorrow - now).total_seconds()) + 10)

def count_today_calls() -> int:
    """çµ±è¨ˆä»Šå¤©(UTC)å·²å¯«å…¥ CSV çš„ç­†æ•¸ï¼Œç”¨ä¾†æŽ§ç®¡æ¯æ—¥é…é¡ã€‚"""
    path = today_csv_path() # âœ… ç”¨æ¯å¤©çš„æª”æ¡ˆï¼Œè€Œä¸æ˜¯å›ºå®š DATA_PATH
    if not path.exists():
        return 0
    today = datetime.now(timezone.utc).date()
    cnt = 0
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = datetime.fromisoformat(row["timestamp"])
            ts = ts.replace(tzinfo=timezone.utc)
            if ts.date() == today:
                cnt += 1
    return cnt

def print_and_save(data: dict):
    """
    å°‡ fetch_prices() çš„çµæžœï¼ˆä¾‹å¦‚ {"BTC":{"USD":...}, ...}ï¼‰
    è½‰æˆå¤šåˆ— CSVï¼štimestamp, symbol, usd
    ä¸¦ä¸”æ¯å¤©è‡ªå‹•æ›æ–°æª”ï¼ˆUTC æ—¥æœŸå‘½åï¼‰
    """
    path = today_csv_path() # ä¾‹å¦‚ data/cryptocompare_prices_20250818.csv
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()

    # æº–å‚™è¦å¯«çš„åˆ—
    ts = datetime.now(timezone.utc).isoformat()
    rows = []
    for sym, entry in (data or {}).items():
        # entry å¯èƒ½æ˜¯ {"USD": 116709.31} é€™ç¨®
        usd = (entry or {}).get("USD")
        if usd is None:
            continue
        rows.append({
            "timestamp": ts,
            "symbol": sym,
            "usd": float(usd),
        })

    if not rows:
        print("No rows to write")
        return

    # ä¾å›ºå®šæ¬„ä½å¯«å…¥
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "symbol", "usd"])
        if new_file:
            writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} rows -> {path}")

def loop_fetch(monthly_calls: int | None = None):
    """
    é€£çºŒæ”¶é›†ï¼š
    - ä¾ç•¶æœˆå¤©æ•¸è¨ˆç®—æ¯æ—¥å¯ç”¨æ¬¡æ•¸ (daily_budget)
    - æ›ç®—å»ºè­°å‘¼å«é–“éš”ç§’æ•¸ (suggested_interval_seconds)
    - è‹¥é”åˆ°ç•¶æ—¥ä¸Šé™ï¼Œç¡åˆ° UTC éš”å¤© 00:00:10 å†ç¹¼çºŒ
    monthly_calls ç‚ºå¯é¸è¦†å¯«å€¼ï¼›ä¸çµ¦å°±ä½¿ç”¨ debug_cryptocompare.py è£¡çš„é è¨­ MONTHLY_CALLS
    """
    now = datetime.now(timezone.utc)
    year, month = now.year, now.month
    # NEW: If no argument is passed,use the default MONTHLY_CALLS
    monthly = monthly_calls if MONTHLY_CALLS is not None else MONTHLY_CALLS
    per_day = daily_budget(year, month, monthly)
    interval = suggested_interval_seconds(year, month, monthly)

    print(f"[collector] {year}-{month:02d} ç›®æ¨™/æ—¥ â‰ˆ {per_day} æ¬¡ï¼Œé–“éš” â‰ˆ {interval}s")

    while True:
        # è·¨æœˆå³é‡ç®—é…é¡èˆ‡é–“éš”
        now = datetime.now(timezone.utc)
        if (now.year, now.month) != (year, month):
            year, month = now.year, now.month
            per_day = daily_budget(year, month, monthly)
            interval = suggested_interval_seconds(year, month, monthly)
            print(f"[rollover] é€²å…¥ {year}-{month:02d}ï¼›/æ—¥ â‰ˆ {per_day}ï¼Œé–“éš” â‰ˆ {interval}s")

        used_today = count_today_calls()
        if used_today >= per_day:
            sleep_s = seconds_until_tomorrow_utc()
            print(f"[quota] ä»Šæ—¥å·²é” {used_today}/{per_day}ï¼Œä¼‘æ¯ {sleep_s}s åˆ° UTC æ˜Žå¤©â€¦")
            time.sleep(sleep_s)
            continue

        try:
            data = fetch_prices()
            print_and_save(data)
        except Exception as e:
            print("Error:", e)

        time.sleep(interval)

                      # è¨­å®š API keyï¼ˆæ¯å€‹æ–°é–‹è¦–çª—è¦è¨­ä¸€æ¬¡ï¼‰
        $env:CRYPTOCOMPARE_API_KEY = 'ä½ çš„APIé‡‘é‘°'

                     # é è¨­ 11000/æœˆï¼š
        python .\collect_cryptocompare.py

                      # æˆ–è¦†å¯«æœˆé…é¡ï¼ˆä¾‹å¦‚ 9000/æœˆï¼‰ï¼š
        python .\collect_cryptocompare.py 9000



if __name__ == "__main__":
    # å¯é¸ï¼šè¦†å¯«æœˆé…é¡ï¼Œä¾‹ï¼šloop_fetch(11000)
    loop_fetch()

