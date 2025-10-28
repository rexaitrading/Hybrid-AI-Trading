import json, urllib.request, urllib.error, re
from typing import Any, Dict, Tuple

class Client:
    """
    Minimal CryptoCompare client.
    kwargs:
      key (optional) -> X-CMC_PRO_API_KEY style? (CryptoCompare uses authorization via query param 'api_key' for some plans.)
      base default https://min-api.cryptocompare.com
    """
    def __init__(self, key: str = "", base: str = "https://min-api.cryptocompare.com", **_):
        self.key  = key or ""
        self.base = base.rstrip("/")

    @staticmethod
    def _norm_pair(sym: str) -> Tuple[str,str]:
        s = (sym or "").upper().strip()
        if "/" in s: b,q = s.split("/",1); return b,q
        if "-" in s: b,q = s.split("-",1); return b,q
        if "_" in s: b,q = s.split("_",1); return b,q
        m = re.match(r"^([A-Z0-9]+?)(USDT|USDC|USD|EUR|CAD)$", s)
        if m: return m.group(1), m.group(2)
        return s, "USD"

    def _http_json(self, url: str, timeout=6) -> Dict[str, Any]:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            return {"_error": f"{type(e).__name__}: {e}"}

    def last_quote(self, symbol: str) -> Dict[str,Any]:
        base, quote = self._norm_pair(symbol)
        # /data/price?fsym=BTC&tsyms=USD,USDT
        api_key_q = f"&api_key={self.key}" if self.key else ""
        url = f"{self.base}/data/price?fsym={base}&tsyms={quote}{api_key_q}"
        j = self._http_json(url)
        if isinstance(j, dict) and "_error" not in j:
            if "Response" in j and j.get("Response") == "Error":
                return {"symbol": symbol, "price": None, "source": "cryptocompare", "reason": j.get("Message") or "error"}
            if quote in j and isinstance(j[quote], (int,float)):
                return {"symbol": symbol, "price": float(j[quote]), "source": "cryptocompare"}
            return {"symbol": symbol, "price": None, "source": "cryptocompare", "reason": "no_rate"}
        return {"symbol": symbol, "price": None, "source": "cryptocompare", "reason": j.get("_error") if isinstance(j,dict) else "http_error"}
