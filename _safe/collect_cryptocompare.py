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
    """回傳今天（UTC）對應的每日檔名"""
    d = datetime.now(timezone.utc).strftime("%Y%m%d")
    return base_dir / f"cryptocompare_prices_{d}.csv"


def seconds_until_tomorrow_utc() -> int:
    """回傳距離 UTC 明天 00:00 的秒數，多加 10 秒緩衝。"""
    now = datetime.now(timezone.utc)
    midnight_tomorrow = datetime.combine(
        (now + timedelta(days=1)).date(), datetime.min.time(), tzinfo=timezone.utc
    )
    return max(1, int((midnight_tomorrow - now).total_seconds()) + 10)

def count_today_calls() -> int:
    """統計今天(UTC)已寫入 CSV 的筆數，用來控管每日配額。"""
    path = today_csv_path() # ✅ 用每天的檔案，而不是固定 DATA_PATH
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
    將 fetch_prices() 的結果（例如 {"BTC":{"USD":...}, ...}）
    轉成多列 CSV：timestamp, symbol, usd
    並且每天自動換新檔（UTC 日期命名）
    """
    path = today_csv_path() # 例如 data/cryptocompare_prices_20250818.csv
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()

    # 準備要寫的列
    ts = datetime.now(timezone.utc).isoformat()
    rows = []
    for sym, entry in (data or {}).items():
        # entry 可能是 {"USD": 116709.31} 這種
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

    # 依固定欄位寫入
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "symbol", "usd"])
        if new_file:
            writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} rows -> {path}")

def loop_fetch(monthly_calls: int | None = None):
    """
    連續收集：
    - 依當月天數計算每日可用次數 (daily_budget)
    - 換算建議呼叫間隔秒數 (suggested_interval_seconds)
    - 若達到當日上限，睡到 UTC 隔天 00:00:10 再繼續
    monthly_calls 為可選覆寫值；不給就使用 debug_cryptocompare.py 裡的預設 MONTHLY_CALLS
    """
    now = datetime.now(timezone.utc)
    year, month = now.year, now.month
    # NEW: If no argument is passed,use the default MONTHLY_CALLS
    monthly = monthly_calls if MONTHLY_CALLS is not None else MONTHLY_CALLS
    per_day = daily_budget(year, month, monthly)
    interval = suggested_interval_seconds(year, month, monthly)

    print(f"[collector] {year}-{month:02d} 目標/日 ≈ {per_day} 次，間隔 ≈ {interval}s")

    while True:
        # 跨月即重算配額與間隔
        now = datetime.now(timezone.utc)
        if (now.year, now.month) != (year, month):
            year, month = now.year, now.month
            per_day = daily_budget(year, month, monthly)
            interval = suggested_interval_seconds(year, month, monthly)
            print(f"[rollover] 進入 {year}-{month:02d}；/日 ≈ {per_day}，間隔 ≈ {interval}s")

        used_today = count_today_calls()
        if used_today >= per_day:
            sleep_s = seconds_until_tomorrow_utc()
            print(f"[quota] 今日已達 {used_today}/{per_day}，休息 {sleep_s}s 到 UTC 明天…")
            time.sleep(sleep_s)
            continue

        try:
            data = fetch_prices()
            print_and_save(data)
        except Exception as e:
            print("Error:", e)

        time.sleep(interval)

                      # 設定 API key（每個新開視窗要設一次）
        $env:CRYPTOCOMPARE_API_KEY = '你的API金鑰'

                     # 預設 11000/月：
        python .\collect_cryptocompare.py

                      # 或覆寫月配額（例如 9000/月）：
        python .\collect_cryptocompare.py 9000



if __name__ == "__main__":
    # 可選：覆寫月配額，例：loop_fetch(11000)
    loop_fetch()
