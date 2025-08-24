import os
import requests
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

# 從 .env 讀取金鑰
COINAPI_KEY = os.getenv("bd4e0dc3-8de0-44e2-8894-c6e3d491f8a3")

if not COINAPI_KEY:
    print("❌ MISSING: COINAPI_KEY not found in .env")
    exit(1)

print("✅ COINAPI_KEY loaded successfully")

# 測試 API (CoinAPI status endpoint)
url = "https://rest.coinapi.io/v1/exchangerate/BTC/USD"
headers = {"X-CoinAPI-Key": COINAPI_KEY}

try:
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        print("✅ CoinAPI connection OK")
        print("BTC/USD rate:", data.get("rate"))
    else:
        print("❌ Error:", response.status_code, response.text)
except Exception as e:
    print("❌ Exception while calling CoinAPI:", e)