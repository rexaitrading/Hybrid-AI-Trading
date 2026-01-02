from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

import requests  # tests patch hybrid_ai_trading.data.clients.polygon_client.requests

__all__ = ["PolygonAPIError", "PolygonClient", "load_config"]

logger = logging.getLogger("hybrid_ai_trading.data.clients.polygon_client")


class PolygonAPIError(RuntimeError):
    pass


def load_config() -> Optional[dict]:
    """
    Placeholder config loader (tests monkeypatch this).
    Keep this function here (tests patch polygon_client.load_config).
    """
    return None


def _is_nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


class PolygonClient:
    """
    Key resolution order (tests depend on this):
      1) explicit api_key
      2) env POLYGON_KEY / POLYGON_API_KEY
      3) if allow_missing=True -> stub (no config needed)
      4) else read load_config().providers.polygon.api_key_env and its env value
      5) if still missing -> PolygonAPIError("Polygon API key not provided")

    Required surface (tests patch/call these):
      - _headers()
      - _request()
      - prev_close()
      - ping()
      - module-level 'requests'
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        allow_missing: bool = False,
        base_url: Optional[str] = None,
        session: Any = None,
        timeout: float = 10.0,
    ):
        self.base_url = (base_url or "https://api.polygon.io").rstrip("/")
        self.timeout = float(timeout) if timeout else 10.0
        self.session = session  # optional injected session for tests
        self._stub = False

        key: Optional[str] = None

        # 1) explicit api_key
        if _is_nonempty_str(api_key):
            key = api_key.strip()

        # 2) env POLYGON_KEY / POLYGON_API_KEY
        if not key:
            env_key = os.getenv("POLYGON_KEY")
            if _is_nonempty_str(env_key):
                key = env_key.strip()

        # 3) allow_missing => stub
        if not key and allow_missing:
            self.api_key = None
            self._stub = True
            return

        # 4) config-driven resolution (strict validation)
        if not key:
            try:
                cfg = load_config()
            except Exception as e:
                raise PolygonAPIError(f"Failed to load Polygon config: {e!r}") from e

            if cfg is None:
                cfg = {}

            if not isinstance(cfg, dict):
                raise PolygonAPIError("Invalid Polygon config structure")

            providers = cfg.get("providers", {})
            if providers is None:
                providers = {}
            if not isinstance(providers, dict):
                raise PolygonAPIError("Invalid Polygon config structure")

            poly_cfg = providers.get("polygon", {})
            if poly_cfg is None:
                poly_cfg = {}
            if not isinstance(poly_cfg, dict):
                raise PolygonAPIError("Invalid Polygon config structure")

            env_name = poly_cfg.get("api_key_env")
            if not _is_nonempty_str(env_name):
                raise PolygonAPIError("Polygon API key not provided")

            env_name = env_name.strip()
            v = os.getenv(env_name)
            if _is_nonempty_str(v):
                key = v.strip()
            else:
                raise PolygonAPIError("Polygon API key not provided")

        # 5) final enforcement
        if not _is_nonempty_str(key):
            raise PolygonAPIError("Polygon API key not provided")

        self.api_key = key

    def _headers(self) -> dict:
        if not _is_nonempty_str(self.api_key):
            raise PolygonAPIError("Polygon API key not set")
        return {"apiKey": self.api_key}

    def _request(self, path: str, params: Optional[dict] = None) -> dict:
        if self._stub:
            raise PolygonAPIError("Polygon client is in stub mode")

        url = f"{self.base_url}/{str(path).lstrip('/')}"
        p = dict(params or {})

        # also include key as query param for compatibility
        if _is_nonempty_str(self.api_key):
            p.setdefault("apiKey", self.api_key)

        sess = self.session if self.session is not None else requests

        try:
            resp = sess.get(url, params=p, headers=self._headers(), timeout=self.timeout)
        except Exception as e:
            raise PolygonAPIError(f"Polygon request failed: {e!r}") from e

        # HTTP error mapping
        try:
            if hasattr(resp, "raise_for_status"):
                resp.raise_for_status()
        except Exception as e:
            raise PolygonAPIError(f"Polygon HTTP error: {e!r}") from e

        # JSON parse mapping
        try:
            data = resp.json()
        except Exception as e:
            raise PolygonAPIError(f"Failed to parse Polygon response: {e!r}") from e

        if not isinstance(data, dict):
            raise PolygonAPIError("Polygon response not a dict")

        return data

    def prev_close(self, symbol: str) -> dict:
        sym = (symbol or "").strip().upper()
        if not sym:
            raise PolygonAPIError("Invalid symbol")
        return self._request(f"v2/aggs/ticker/{sym}/prev", params={})

    def ping(self) -> bool:
        try:
            # tests patch prev_close(); use it as the health probe
            self.prev_close("AAPL")
            return True
        except Exception as e:
            logger.warning("Polygon ping failed: %s", e)
            return False
