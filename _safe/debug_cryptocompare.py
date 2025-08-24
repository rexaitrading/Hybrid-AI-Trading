# -*- coding: utf-8 -*-
import os
import json
import csv
import time
import requests
import calendar
from datetime import datetime, timezone
from datetime import datetime, timezone 
from pathlib import Path


# ---- 設定 ----
API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY") # 建議用環境變數；若沒有就填下一行
# API_KEY = "11000"

URL = "https://min-api.cryptocompare.com/data/pricemulti"
SYMBOLS = ["BTC", "ETH", "SOL"]
PARAMS = {"fsyms": ",".join(SYMBOLS), "tsyms": "USD"}
HEADERS = {"authorization": f"Apikey {API_KEY}"} if API_KEY else {}

def fetch_prices():
    """呼叫 API（含簡單重試/退避）"""
    for attempt in range(3):
        try:
            r = requests.get(URL, params=PARAMS, headers=HEADERS, timeout=10)
            print("HTTP status:", r.status_code)
            print("Raw body:", r.text[:300])
            if r.status_code == 429:
                raise RuntimeError("Rate limited (429), try again later.")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(1.5 * (attempt + 1))

def print_and_save(data):
    """Pretty print and append to CSV."""
    # Console table
    print("\nSYMBOL PRICE(USD)")
    print("-" * 24)

    rows = []
    for sym in SYMBOLS:
        usd = data.get(sym, {}).get("USD")
        if usd is None:
            print(f"{sym:<6} N/A")
            continue
        print(f"{sym:<6} {usd:,.2f}")
        rows.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "symbol": sym,
            "usd": usd
        })

def days_in_month(year: int, month: int) -> int:
    # 回傳當月天數，calendar 會自動處理閏年（8 月 18）
    return calendar.monthrange(year, month)[1]

def is_valid_date(y: int, m: int, d: int) -> bool:
    # 試著建立 datetime；若日期非法（如 8/18）會丟 ValueError
    try:
        datetime(y, m, d)
        return True
    except ValueError:
        return False

# ===== 配額設定（依你的方案調整）=====
MONTHLY_CALLS = 11000 # 你現在畫面顯示是 11,000/月

def daily_budget(year: int, month: int, monthly_calls: int = MONTHLY_CALLS) -> int:
    """回傳該月每日可用的平均呼叫數（整數）"""
    d = days_in_month(year, month)
    return max(1, monthly_calls // d)

def suggested_interval_seconds(year: int, month: int, monthly_calls: int = MONTHLY_CALLS) -> int:
    """依每日配額，回傳建議的呼叫間隔秒數（同日均勻分散）"""
    per_day = daily_budget(year, month, monthly_calls)
    sec_per_day = 24 * 60 * 60
    # 均勻分散；保底 1 秒，避免 0
    return max(1, sec_per_day // per_day)


    def main():
        if not API_KEY:
            print("ERROR: Missing API key. Set CRYPTOCOMPARE_API_KEY or hard-code API_KEY.")
            return

        data = fetch_prices()
        print_and_save(data)

# 這裡一定要是 2 個底線，不是 1 個
if __name__ == "__main__":
    main()
