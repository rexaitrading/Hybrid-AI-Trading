import json
import re
import urllib.error
import urllib.request
from typing import Any, Dict, Tuple


class Client:
    """
    Minimal CoinAPI client for crypto pairs.
    Expects kwargs: key (api key), base (e.g., https://rest.coinapi.io)
    last_quote supports symbols like: BTCUSD, BTC/USDT, ETH-USD, eth_usd, etc.
    """

    def __init__(self, key: str, base: str = "https://rest.coinapi.io", **_):
        if not key or not base:
            raise ValueError("coinapi_client.Client requires key and base")
        self.key = key
        self.base = base.rstrip("/")

    def _http_json(self, url: str, headers=None, timeout=6) -> Dict[str, Any]:
        hdrs = {"X-CoinAPI-Key": self.key}
        if headers:
            hdrs.update(headers)
        req = urllib.request.Request(url, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            return {"_error": f"{type(e).__name__}: {e}"}

    @staticmethod
    def _norm_pair(sym: str) -> Tuple[str, str]:
        """
        Normalize a crypto symbol into (base, quote).
        Accepts: BTCUSD, BTC/USD, BTC-USD, btc_usdt -> ('BTC','USD' or 'USDT')
        """
        s = (sym or "").upper().strip()
        if "/" in s:
            parts = s.split("/")
        elif "-" in s:
            parts = s.split("-")
        elif "_" in s:
            parts = s.split("_")
        else:
            # assume last 3-4 letters are quote (USD, USDT, USDC, EUR, CAD)
            m = re.match(r"^([A-Z0-9]+?)(USDT|USDC|USD|EUR|CAD)$", s)
            if m:
                return m.group(1), m.group(2)
            # fallback: unknown split -> default to USD
            return s, "USD"
        if len(parts) == 2:
            return parts[0], parts[1]
        # fallback
        return s, "USD"

    def last_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Uses GET /v1/exchangerate/{base}/{quote}
        Returns: {"symbol": original, "price": rate, "source": "coinapi"} or reason
        """
        base, quote = self._norm_pair(symbol)
        url = f"{self.base}/v1/exchangerate/{base}/{quote}"
        j = self._http_json(url)
        if isinstance(j, dict) and "_error" not in j:
            # shape: {"time": "...", "asset_id_base":"BTC", "asset_id_quote":"USD", "rate": 12345.67}
            rate = j.get("rate")
            if isinstance(rate, (int, float)):
                return {"symbol": symbol, "price": float(rate), "source": "coinapi"}
            # CoinAPI sometimes responds with {"error": "..."} on invalid pairs
            if j.get("error"):
                return {
                    "symbol": symbol,
                    "price": None,
                    "source": "coinapi",
                    "reason": j.get("error"),
                }
            return {
                "symbol": symbol,
                "price": None,
                "source": "coinapi",
                "reason": "no_rate",
            }
        return {
            "symbol": symbol,
            "price": None,
            "source": "coinapi",
            "reason": j.get("_error") if isinstance(j, dict) else "http_error",
        }
