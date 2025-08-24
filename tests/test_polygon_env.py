# tests/test_polygon_env.py
import os
import requests
from dotenv import load_dotenv
from pprint import pprint # ✅ 放最頂

def fail(msg):
    print("❌", msg)
    exit(1)

def main():
    load_dotenv()
    key = os.getenv("POLYGON_KEY")
    if not key:
        fail("未找到 POLYGON_KEY，請先在 .env 檔案加入 POLYGON_KEY")

    url = "https://api.polygon.io/v2/aggs/ticker/AAPL/prev"
    headers = {"Authorization": f"Bearer {key}"}

    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            print("✅ Polygon API OK 回應：")
            pprint(data) # 原始 JSON 美化顯示

            # 🎯 額外顯示重點
            if "results" in data and len(data["results"]) > 0:
                result = data["results"][0]
                print("\n📊 重點數據：")
                print(f"股票代號: {data.get('ticker', 'N/A')}")
                print(f"收市價(c): {result.get('c', 'N/A')}")
                print(f"開市價(o): {result.get('o', 'N/A')}")
                print(f"最高價(h): {result.get('h', 'N/A')}")
                print(f"最低價(l): {result.get('l', 'N/A')}")
                print(f"成交量(v): {result.get('v', 'N/A')}")
                print(f"{data.get('ticker', 'N/A')} 收市: {result.get('c', 'N/A')} | 開市: {result.get('o', 'N/A')} | 高: {result.get('h', 'N/A')} | 低: {result.get('l', 'N/A')} | 量: {result.get('v', 'N/A')}")
        elif r.status_code == 401:
            fail("401 Unauthorized: API Key 錯誤或未啟用")
        elif r.status_code == 403:
            fail("403 Forbidden: API Key 被禁止")
        elif r.status_code == 429:
            fail("429 Too Many Requests: 請求次數超過限制")
        else:
            fail(f"API 請求失敗，狀態碼: {r.status_code}")
    except Exception as e:
        fail(f"請求失敗: {e}")

if __name__ == "__main__":
    main()