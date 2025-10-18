import json, urllib.request, urllib.error, os
from typing import Any, Dict, List

class Client:
    """
    Minimal Polygon News client.
    kwargs: key, base (default https://api.polygon.io)
    """
    def __init__(self, key=None, base=None, **_):
        self.key  = key or os.getenv("POLYGON_KEY","")
        self.base = (base or "https://api.polygon.io").rstrip("/")
        if not self.key:
            raise ValueError("Polygon news requires key")
    def _http_json(self, url: str, timeout=6):
        try:
            req = urllib.request.Request(url, headers={})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            return {"_error": f"{type(e).__name__}: {e}"}
    def latest(self, ticker: str, limit=20) -> Dict[str,Any]:
        url = f"{self.base}/v2/reference/news?ticker={ticker}&limit={int(limit)}&apiKey={self.key}"
        return self._http_json(url)