# tests/test_env.py

import os
from dotenv import load_dotenv
import requests

def fail(msg, code=1):
    print("❌", msg)
    exit(code)

def main():
    # 載入 .env 檔
    load_dotenv()

    # 從環境變數攞 CoinAPI key
    key = os.getenv("COINAPI_KEY")
    if not key:
        fail("未找到 COINAPI_KEY，請先在 .env 填入 COINAPI_KEY")

    # 測試 API 是否能用
    url = "https://rest.coinapi.io/v1/exchangerate/BTC/USD"
    headers = {"X-CoinAPI-Key": key}
    try:
        r = requests.get(url, headers=headers)
    except Exception as e:
        fail(f"請求失敗: {e}")

    if r.status_code == 200:
        print("✅ CoinAPI OK | 回應:", r.json())
    elif r.status_code == 401:
        fail("401 Unauthorized: 金鑰錯誤或無效")
    elif r.status_code == 429:
        fail("429 Too Many Requests: 免費額度用完")
    else:
        fail(f"API 其他錯誤: {r.status_code}, {r.text}")

if __name__ == "__main__":
    main()