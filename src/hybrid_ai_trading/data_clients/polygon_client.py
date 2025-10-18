import json, urllib.request, urllib.error
from typing import Any, Dict

class Client:
    """
    Minimal Polygon client for equities.
    Expects kwargs: key (api key), base (e.g., https://api.polygon.io)
    """
    def __init__(self, key: str, base: str = "https://api.polygon.io", **_):
        if not key or not base:
            raise ValueError("polygon_client.Client requires key and base")
        self.key  = key
        self.base = base.rstrip("/")

    def _http_json(self, url: str, headers=None, timeout=6) -> Dict[str, Any]:
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            return {"_error": f"{type(e).__name__}: {e}"}

    def _pick_price(self, j: Dict[str, Any]):
        """Extract a price from common Polygon shapes."""
        if not isinstance(j, dict):
            return None
        # v3 last trade: {"results":{"price":..., ...}} or {"results":{"p":...}}
        res = j.get("results")
        if isinstance(res, dict):
            p = res.get("price", res.get("p"))
            if isinstance(p, (int, float)):
                return float(p)
        # v2 last trade: {"last":{"price":...}} or {"last":{"p":...}}
        last = j.get("last")
        if isinstance(last, dict):
            p = last.get("price", last.get("p"))
            if isinstance(p, (int, float)):
                return float(p)
        # legacy direct price
        p = j.get("price")
        if isinstance(p, (int, float)):
            return float(p)
        return None

    def last_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Try, in order:
          1) /v3/trades/{ticker}/last
          2) /v2/last/trade/{ticker}
          3) /v2/aggs/ticker/{ticker}/prev (close)
        Returns: {"symbol": ..., "price": float|None, "source": "polygon", "reason"?: str}
        """
        sym = (symbol or "").upper().strip()
        reasons = []

        # 1) v3 last trade
        url1 = f"{self.base}/v3/trades/{sym}/last?apiKey={self.key}"
        j1 = self._http_json(url1)
        p1 = self._pick_price(j1)
        if isinstance(p1, (int, float)):
            return {"symbol": sym, "price": float(p1), "source": "polygon"}
        if isinstance(j1, dict):
            reasons.append(j1.get("status") or j1.get("_error") or "no_price_v3")

        # 2) v2 last trade
        url2 = f"{self.base}/v2/last/trade/{sym}?apiKey={self.key}"
        j2 = self._http_json(url2)
        p2 = self._pick_price(j2)
        if isinstance(p2, (int, float)):
            return {"symbol": sym, "price": float(p2), "source": "polygon"}
        if isinstance(j2, dict):
            reasons.append(j2.get("status") or j2.get("_error") or "no_price_v2")

        # 3) previous day close
        url3 = f"{self.base}/v2/aggs/ticker/{sym}/prev?adjusted=true&apiKey={self.key}"
        j3 = self._http_json(url3)
        if isinstance(j3, dict):
            res = j3.get("results")
            if isinstance(res, list) and res:
                c = res[0].get("c")
                if isinstance(c, (int, float)):
                    return {"symbol": sym, "price": float(c), "source": "polygon"}
            reasons.append(j3.get("status") or j3.get("_error") or "no_prev_close")

        # Aggregate reason; don't short-circuit on benign statuses like DELAYED
        reason = ",".join([r for r in reasons if r]) or "no_price"
        return {"symbol": sym, "price": None, "source": "polygon", "reason": reason}