import os, sys, json, traceback
from dotenv import load_dotenv
import requests

print("=== start ===")
load_dotenv()
k = os.getenv("COINAPI_KEY")
print("COINAPI_KEY present:", k is not None)
print("COINAPI_KEY preview:", (k[:8] + "...") if k else None)

url = "https://rest.coinapi.io/v1/exchangerate/BTC/USD"
headers = {"X-CoinAPI-Key": k or ""}

try:
    r = requests.get(url, headers=headers, timeout=15)
    print("HTTP status:", r.status_code)
    print("Raw body head:", r.text[:200].replace("\n", " ") if     r.text else None)
    r.raise_for_status()
    data = r.json()
    print("Parsed:", json.dumps(
    [{x: data.get(x) for x in ("asset_id_base",     "asset_id_quote", "rate")}],
    indent=2
    ))
except Exception as e:
       print("ERROR:", repr(e))
       traceback.print_exc()

