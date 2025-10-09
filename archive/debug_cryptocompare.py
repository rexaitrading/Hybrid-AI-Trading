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


# ---- è¨­å®š ----
API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")  # å»ºè­°ç”¨ç’°å¢ƒè®Šæ•¸ï¼›è‹¥æ²’æœ‰å°±å¡«ä¸‹ä¸€è¡Œ
# API_KEY = "11000"

URL = "https://min-api.cryptocompare.com/data/pricemulti"
SYMBOLS = ["BTC", "ETH", "SOL"]
PARAMS = {"fsyms": ",".join(SYMBOLS), "tsyms": "USD"}
HEADERS = {"authorization": f"Apikey {API_KEY}"} if API_KEY else {}


def fetch_prices():
    """å‘¼å« APIï¼ˆå«ç°¡å–®é‡è©¦/é€€é¿ï¼‰"""
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
        rows.append({"ts": datetime.now(timezone.utc).isoformat(), "symbol": sym, "usd": usd})


def days_in_month(year: int, month: int) -> int:
    # å›žå‚³ç•¶æœˆå¤©æ•¸ï¼Œcalendar æœƒè‡ªå‹•è™•ç†é–å¹´ï¼ˆ8 æœˆ 18ï¼‰
    return calendar.monthrange(year, month)[1]


def is_valid_date(y: int, m: int, d: int) -> bool:
    # è©¦è‘—å»ºç«‹ datetimeï¼›è‹¥æ—¥æœŸéžæ³•ï¼ˆå¦‚ 8/18ï¼‰æœƒä¸Ÿ ValueError
    try:
        datetime(y, m, d)
        return True
    except ValueError:
        return False


# ===== é…é¡è¨­å®šï¼ˆä¾ä½ çš„æ–¹æ¡ˆèª¿æ•´ï¼‰=====
MONTHLY_CALLS = 11000  # ä½ ç¾åœ¨ç•«é¢é¡¯ç¤ºæ˜¯ 11,000/æœˆ


def daily_budget(year: int, month: int, monthly_calls: int = MONTHLY_CALLS) -> int:
    """å›žå‚³è©²æœˆæ¯æ—¥å¯ç”¨çš„å¹³å‡å‘¼å«æ•¸ï¼ˆæ•´æ•¸ï¼‰"""
    d = days_in_month(year, month)
    return max(1, monthly_calls // d)


def suggested_interval_seconds(year: int, month: int, monthly_calls: int = MONTHLY_CALLS) -> int:
    """ä¾æ¯æ—¥é…é¡ï¼Œå›žå‚³å»ºè­°çš„å‘¼å«é–“éš”ç§’æ•¸ï¼ˆåŒæ—¥å‡å‹»åˆ†æ•£ï¼‰"""
    per_day = daily_budget(year, month, monthly_calls)
    sec_per_day = 24 * 60 * 60
    # å‡å‹»åˆ†æ•£ï¼›ä¿åº• 1 ç§’ï¼Œé¿å… 0
    return max(1, sec_per_day // per_day)

    def main():
        if not API_KEY:
            print("ERROR: Missing API key. Set CRYPTOCOMPARE_API_KEY or hard-code API_KEY.")
            return

        data = fetch_prices()
        print_and_save(data)


# é€™è£¡ä¸€å®šè¦æ˜¯ 2 å€‹åº•ç·šï¼Œä¸æ˜¯ 1 å€‹
if __name__ == "__main__":
    main()
