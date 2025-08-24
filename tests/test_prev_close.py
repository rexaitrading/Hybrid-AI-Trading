# tests/test_prev_close.py
from pprint import pprint
from utils.config import load_config
from utils.universe import Core_Stocks
from utils.polygon import PolygonClient

def main():
    # 1) 讀 config.yaml
    cfg = load_config()
    print("⚙ 已載入設定:")
    print("- 時區:", cfg.get("timezone"))
    print("- 目標日回報:", cfg.get("risk", {}).get("target_daily_return"))
    print("- 股票清單(前5支):", Core_Stocks[:5])

    # 2) 建立 Polygon Client（使用 .env 入面的 POLYGON_KEY）
    client = PolygonClient()

    # 3) 測試多組資產
    asset_groups = {
        "Core_Stocks": Core_Stocks,
        "Crypto_Signal": Crypto_Signal,
        "Macro_Risk": Macro_Risk,
        "Leverage_Tools": Leverage_Tools,
        "IPO_Watch": IPO_Watch,
    }

    for group, symbols in asset_groups.items():
        print(f"\n📊 測試 {group}:")
        if not symbols:
            print(f"⚠️ {group} 無清單")
            continue

        for symbol in symbols:
            print(f"\n🔎 測試前日收市: {symbol}")
            try:
                data = client.prev_close(symbol)
                if "results" in data and len(data["results"]) > 0:
                    r = data["results"][0]
                    print(f"✅ {symbol} 收市: {r['c']} | 開: {r['o']} 高: {r['h']} 低: {r['l']} 量: {r['v']}")
                else:
                    print(f"⚠️ {symbol} 無數據: {data}")
            except Exception as e:
                print(f"❌ {symbol} 錯誤: {e}")

if __name__ == "__main__":
    main()