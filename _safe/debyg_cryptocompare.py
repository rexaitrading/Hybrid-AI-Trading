import os, json, requests, sys

# Get API key from environment
API_KEY = os.getenv("CRYPTOCOMPARE_KEY") or "PUT_YOUR_CRYPTOCOMPARE_KEY_HERE"

def main():
    if not API_KEY or API_KEY.startswith("PUT_"):
        print("ERROR: Missing CryptoCompare key. Set CRYPTOCOMPARE_KEY or edit the file.")
        sys.exit(1)

    url = "https://min-api.cryptocompare.com/data/pricemulti"
    params = {"fsyms": "BTC,ETH,SOL", "tsyms": "USD"
    headers = {"authorization": f"Apikey {API_KEY}"}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        print("HTTP status:", r.status_code)
        r.raise_for_status()
        data = r.json()
        print("\nParsed:")
        print(json.dumps(data, indent=2))
    except Exception as e:
print("ERROR:", repr(e))

if __name__ == "__main__":
    main()

