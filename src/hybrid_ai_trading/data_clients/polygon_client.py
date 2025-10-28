import json, urllib.request, urllib.error
from typing import Any, Dict

class Client:
    """
    Minimal Polygon client for equities, some currencies, and CL1! best-effort.
    kwargs: key (api key), base (e.g., https://api.polygon.io)
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
        if not isinstance(j, dict):
            return None
        # v3 last trade
        res = j.get("results")
        if isinstance(res, dict):
            p = res.get("price", res.get("p"))
            if isinstance(p, (int, float)):
                return float(p)
        # v2 last trade
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

    def _is_fx_6(self, s: str) -> bool:
        s = (s or "").upper()
        return len(s) == 6 and s.isalpha()

    def last_quote(self, symbol: str) -> Dict[str, Any]:
        sym = (symbol or "").upper().strip()

        # Special case: continuous oil future -> try C:CL1! previous close
        if sym == "CL1!":
            urlc = f"{self.base}/v2/aggs/ticker/C:CL1!/prev?adjusted=true&apiKey={self.key}"
            jc = self._http_json(urlc)
            if isinstance(jc, dict):
                res = jc.get("results")
                if isinstance(res, list) and res:
                    c = res[0].get("c")
                    if isinstance(c, (int, float)):
                        return {"symbol": sym, "price": float(c), "source": "polygon"}

        # FX 6-letter pairs (e.g., USDJPY/EURUSD) -> try C:<PAIR> previous close
        if self._is_fx_6(sym):
            urlf = f"{self.base}/v2/aggs/ticker/C:{sym}/prev?adjusted=true&apiKey={self.key}"
            jf = self._http_json(urlf)
            if isinstance(jf, dict):
                res = jf.get("results")
                if isinstance(res, list) and res:
                    c = res[0].get("c")
                    if isinstance(c, (int, float)):
                        return {"symbol": sym, "price": float(c), "source": "polygon"}

        # 1) v3 last trade
        url1 = f"{self.base}/v3/trades/{sym}/last?apiKey={self.key}"
        j1 = self._http_json(url1)
        p1 = self._pick_price(j1)
        if isinstance(p1, (int, float)):
            return {"symbol": sym, "price": float(p1), "source": "polygon"}

        # 2) v2 last trade
        url2 = f"{self.base}/v2/last/trade/{sym}?apiKey={self.key}"
        j2 = self._http_json(url2)
        p2 = self._pick_price(j2)
        if isinstance(p2, (int, float)):
            return {"symbol": sym, "price": float(p2), "source": "polygon"}

        # 3) previous day close
        url3 = f"{self.base}/v2/aggs/ticker/{sym}/prev?adjusted=true&apiKey={self.key}"
        j3 = self._http_json(url3)
        if isinstance(j3, dict):
            res = j3.get("results")
            if isinstance(res, list) and res:
                c = res[0].get("c")
                if isinstance(c, (int, float)):
                    return {"symbol": sym, "price": float(c), "source": "polygon"}

        reason = None
        for j in (j1, j2, j3):
            if isinstance(j, dict):
                reason = reason or j.get("_error") or j.get("status")
        # If CL1! not available on this plan, try USO ETF as a proxy (prev close)
        if sym == "CL1!":
            urlu = f"{self.base}/v2/aggs/ticker/USO/prev?adjusted=true&apiKey={self.key}"
            ju = self._http_json(urlu)
            if isinstance(ju, dict):
                resu = ju.get("results")
                if isinstance(resu, list) and resu:
                    cu = resu[0].get("c")
                    if isinstance(cu, (int, float)):
                        return {"symbol": sym, "price": float(cu), "source": "polygon(USO-proxy)"}
        return {"symbol": sym, "price": None, "source": "polygon", "reason": reason or "no_price"}
