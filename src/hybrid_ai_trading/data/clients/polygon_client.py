"""
Polygon Client (Hybrid AI Quant Pro v1.5 - Safe & Test-Friendly)
----------------------------------------------------------------
- __init__(api_key=None, allow_missing=False, base_url=..., session=None, timeout=10.0)
- Key resolution order:
    1) explicit api_key
    2) env POLYGON_KEY / POLYGON_API_KEY
    3) if allow_missing=True -> stub (no config needed)
    4) else read load_config().providers.polygon.api_key_env and its env value
- _headers(): {"apiKey": <key>} or raises if missing
- _request(): GET with query param auth; robust error mapping
- prev_close(): wrapper for /v2/aggs/ticker/{symbol}/prev
- ping(): True on success; warns and False on PolygonAPIError; False on generic Exception
"""

from __future__ import annotations
from typing import Any, Dict, Optional
import os
import logging

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore

__all__ = ["PolygonAPIError", "PolygonClient", "load_config"]

logger = logging.getLogger("hybrid_ai_trading.data.clients.polygon_client")


class PolygonAPIError(Exception):
    """Polygon client error."""


def load_config() -> Optional[dict]:
    """
    Placeholder config loader (tests monkeypatch this).
    Real app may import a central settings loader here.
    """
    return None


class PolygonClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        allow_missing: bool = False,
        base_url: Optional[str] = None,
        session: Any = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = (base_url or "https://api.polygon.io").rstrip("/")
        self.session = session
        self.timeout = timeout

        # 1) explicit api_key
        key = api_key

        # 2) env fallback
        if not key:
            key = os.getenv("POLYGON_KEY") or os.getenv("POLYGON_API_KEY")

        # 3) if still no key and allow_missing=True -> stub (skip config entirely)
        if not key and allow_missing:
            self.api_key: Optional[str] = None
            self._stub = True
            return

        # 4) otherwise resolve via config (tests patch load_config to drive branches)
        if not key:
            try:
                cfg = load_config()
            except Exception as e:
                raise PolygonAPIError(f"Failed to load Polygon config: {e}") from e

            if not isinstance(cfg, dict):
                raise PolygonAPIError("Invalid Polygon config structure")

            providers = cfg.get("providers")
            if providers is None:
                # No providers section -> treat as "key not provided" per tests
                raise PolygonAPIError("Polygon API key not provided")
            if not isinstance(providers, dict):
                raise PolygonAPIError("Invalid Polygon config structure")

            poly_cfg = providers.get("polygon")
            if not isinstance(poly_cfg, dict):
                raise PolygonAPIError("Invalid Polygon config structure")

            env_name = poly_cfg.get("api_key_env")
            if not env_name:
                raise PolygonAPIError("Polygon API key not provided")

            env_val = os.getenv(str(env_name))
            if not env_val:
                raise PolygonAPIError("Polygon API key not provided")

            key = env_val

        self.api_key = key
        self._stub = False

    # ---------------- internals ----------------
    def _headers(self) -> Dict[str, str]:
        """
        Tests expect query-param style key surfaced via headers() for inspection.
        """
        if not self.api_key:
            raise PolygonAPIError("Polygon API key not set")
        return {"apiKey": self.api_key}

    def _request(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        GET wrapper that:
        - attaches ?apiKey=... (query param auth)
        - returns dict JSON or raises PolygonAPIError on any anomaly
        """
        if self._stub:
            return {"results": []}

        if requests is None:  # pragma: no cover
            raise PolygonAPIError("requests not available")

        url = f"{self.base_url}/{path.lstrip('/')}"
        q = dict(params or {})
        q.setdefault("apiKey", self._headers()["apiKey"])

        try:
            if self.session is not None:
                resp = self.session.get(url, params=q, timeout=self.timeout)
            else:
                resp = requests.get(url, params=q, timeout=self.timeout)

            # may raise any Exception per tests
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            msg = str(e)
            if isinstance(e, ValueError):
                # json decode error
                raise PolygonAPIError("Failed to parse Polygon response") from e
            raise PolygonAPIError(msg) from e

        if not isinstance(data, dict):
            raise PolygonAPIError("Polygon response not a dict")
        return data

    # ---------------- public API ----------------
    def prev_close(self, symbol: str) -> Dict[str, Any]:
        """Return previous-day aggregate for the ticker."""
        return self._request(f"v2/aggs/ticker/{symbol}/prev")

    def ping(self) -> bool:
        try:
            _ = self.prev_close("AAPL")
            return True
        except PolygonAPIError as e:
            logger.warning("Polygon ping failed: %s", e)
            return False
        except Exception:
            return False
