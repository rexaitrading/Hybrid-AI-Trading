import json, urllib.request, urllib.error
from typing import Any, Dict

# Minimal Kraken client for public ticker prices (no auth required).
# Expects kwargs: base (default https://api.kraken.com)

_PAIR_MAP = {
    # BTC
    "BTCUSD": "XBTUSD", "BTC/USDT": "XBTUSDT", "BTCUSDT": "XBTUSDT",
    "BTC/EUR": "XBTEUR", "BTCEUR": "XBTEUR",
    # ETH
    "ETHUSD": "ETHUSD", "ETH/USDT": "ETHUSDT", "ETHUSDT": "ETHUSDT",
    "ETH/EUR": "ETHEUR", "ETHEUR": "ETHEUR",
    # SOL
    "SOLUSD": "SOLUSD", "SOL/USDT": "SOLUSDT", "SOLUSDT": "SOLUSDT",
}

def _norm_pair(symbol: str) -> str:
    s = (symbol or "").upper().replace("-", "/").strip()
    if s in _PAIR_MAP:
        return _PAIR_MAP[s]
    s2 = s.replace("/", "")  # BTC/USDC -> BTCUSDC
    return _PAIR_MAP.get(s2, s2)  # fallback: raw BTCUSDC etc.

class Client:
    def __init__(self, base: str = "https://api.kraken.com", **_):
        if not base:
            raise ValueError("kraken_client.Client requires base URL")
        self.base = base.rstrip("/")

    def _http_json(self, url: str, headers=None, timeout=6) -> Dict[str, Any]:
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            return {"_error": f"{type(e).__name__}: {e}"}

    def last_quote(self, symbol: str) -> Dict[str, Any]:
        """
        GET /0/public/Ticker?pair=<PAIR>
        Parse result[PAIR]['c'][0] as last trade price
        """
        pair = _norm_pair(symbol)
        url  = f"{self.base}/0/public/Ticker?pair={pair}"
        j = self._http_json(url)
        if not isinstance(j, dict):
            return {"symbol": symbol, "price": None, "source": "kraken", "reason": "bad_json"}
        if j.get("error"):
            return {"symbol": symbol, "price": None, "source": "kraken", "reason": ";".join(j.get("error") or [])}
        res = j.get("result")
        if isinstance(res, dict):
            # Kraken sometimes returns different canonical keys; locate the first
            for key, val in res.items():
                if isinstance(val, dict):
                    c = val.get("c")
                    if isinstance(c, list) and c and isinstance(c[0], str):
                        try:
                            p = float(c[0])
                            return {"symbol": symbol, "price": p, "source": "kraken"}
                        except Exception:
                            pass
        return {"symbol": symbol, "price": None, "source": "kraken", "reason": "no_price"}