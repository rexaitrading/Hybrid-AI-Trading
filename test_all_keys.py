import os
import requests
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

def test_polygon():
    key = os.getenv("dg9YCsmMS3FIAwsf1OkjnBX2xvelb3fX")
    url = f"https://api.polygon.io/v2/aggs/ticker/AAPL/prev?apiKey={key}"
    r = requests.get(url)
    print("Polygon:", r.status_code, r.json().get("status", "No status"))

def test_coinapi():
    key = os.getenv("bd4e0dc3-8de0-44e2-8894-c6e3d491f8a3")
    url = "https://rest.coinapi.io/v1/exchangerate/BTC/USD"
    headers = {"X-CoinAPI-Key": key}
    r = requests.get(url, headers=headers)
    print("CoinAPI:", r.status_code)

def test_alpaca():
    key = os.getenv("PK66817E4JPYYI9BFVCR")
    secret = os.getenv("Nc7j4BramB0SXWTsHd3UcieLfelxLdWIEorkRboV**")
    url = "https://paper-api.alpaca.markets/v2/account"
    r = requests.get(url, headers={
    "APCA-API-KEY-ID": key,
    "APCA-API-SECRET-KEY": secret
    })
    print("Alpaca:", r.status_code)

def test_benzinga():
    key = os.getenv("bz.SOVFSXG7PUMSN57OBMVWLLRMU7XJNNZJ")
    url = f"https://api.benzinga.com/api/v2.1/calendar/earnings?token={key}"
    r = requests.get(url)
    print("Benzinga:", r.status_code)

if __name__ == "__main__":
    test_polygon()
    test_coinapi()
    test_alpaca()
    test_benzinga()
