import requests

API_KEY = "dg9YCsmMS3FIAwsf1OkjnBX2xvelb3fX" # <— 用你屏幕見到的同一個 Polygon API Key
ticker = "AAPL"
url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev?adjusted=true&apiKey={API_KEY}"

resp = requests.get(url)
print("Status Code:", resp.status_code)
print("Response:", resp.json())
project: HybridAI
timezone: America/Vancouver

trading_window:
start:  "05:00" # 開盤時間（你設定嘅時間窗）
end: "11:00"

risk:
target_daily_return: 0.015 # 1.5% 介乎 1–2%
max_daily_loss: 0.02 # 每日最大虧損（硬性止蝕）
max_position_risk: 0.01 # 每隻倉位最大風險（佔淨值）

leverage:
stocks: 2
crypto: 3
forex: 10

providers:
polygon:
api_key_env: dg9YCsmMS3FIAwsf1OkjnBX2xvelb3fX
alpaca:
key_id_env: PK66817E4JPYYI9BFVCR
secret_key_env: Nc7j4BramB0SXWTsHd3UcieLfelxLdWIEorkRboV**

universe:
stocks: ["AAPL","TSLA","NVDA","AMZN","MSFT"]
crypto: ["BTCUSD","ETHUSD"]
forex: ["EURUSD","USDJPY"]

features:
enable_black_swan_guard: true

