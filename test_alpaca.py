import os, requests
from dotenv import load_dotenv

load_dotenv()

key = (os.getenv("PK66817E4JPYYI9BFVCR") or "").strip()
secret = (os.getenv("Nc7j4BramB0SXWTsHd3UcieLfelxLdWIEorkRboV**") or "").strip()
base_url = "https://paper-api.alpaca.markets"

print("ALPACA_KEY length:", len(key))
print("ALPACA_SECRET length:", len(secret))

# ⬇️ 注意：這裡的 print 要縮排 4 個空格
if not key or not secret:
    print("❌ Missing ALPACA_KEY / ALPACA_SECRET environment variables.")
    raise SystemExit()

url = f"{base_url}/v2/account"
r = requests.get(url, headers={
    "APCA-API-KEY-ID": key,
    "APCA-API-SECRET-KEY": secret
}, timeout=15)

print("Status:", r.status_code)
try:
    print("Body:", r.json())
except Exception as e:
    print("Body (text):", r.text)
