# tests/test_crypto_demo.py
import os, json
from datetime import datetime as dt
import requests
from dotenv import load_dotenv

# 讀取 .env 檔案
load_dotenv() 

# Debug print，檢查 API key 是否讀到
# print("DEBUG - COINAPI_KEY:", os.getenv("COINAPI_KEY"))

API = os.getenv("COINAPI_KEY")
BASE = "https://rest.coinapi.io"
HEAD = {"X-CoinAPI-Key": API}

def rate(symbol: str, quote="USD"):
    r = requests.get(f"{BASE}/v1/exchangerate/{symbol}/{quote}", headers=HEAD, timeout=10)
    r.raise_for_status()
    data = r.json()
    return data["rate"], data.get("time")

def main():
    for s in ["BTC", "ETH"]:
        px, t = rate(s, "USD")
        print(f"{s}/USD rate={px:.2f} time={t}")

if __name__ == "__main__":
    main()