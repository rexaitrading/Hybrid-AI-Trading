"""
debug_cryptocompare.py
Quick one-shot fetch from CryptoCompare for debugging / sanity checks.
"""

import json
import os
import sys

import requests

# === API Key Handling =====================================================
API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY")
if not API_KEY:
    print(
        "? Missing CryptoCompare key.\n"
        'Set it with: setx CRYPTOCOMPARE_API_KEY "your_key_here" '
        "and restart your terminal."
    )
    sys.exit(1)


def main():
    url = "https://min-api.cryptocompare.com/data/pricemulti"
    params = {"fsyms": "BTC,ETH,SOL", "tsyms": "USD"}
    headers = {"authorization": f"Apikey {API_KEY}"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        print("HTTP status:", response.status_code)
        response.raise_for_status()

        data = response.json()
        print("\n? Parsed result:")
        print(json.dumps(data, indent=2))
    except Exception as e:
        print("? ERROR:", repr(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
