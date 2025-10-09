from __future__ import annotations

import time
from datetime import datetime
from datetime import timezone as tz
from typing import Optional

import requests

from src.config.settings import load_config

# Explicit exports (but private helpers are still available for tests)
__all__ = [
    "get_fx_rate",
    "get_ohlcv_latest",
    "ping",
    "CoinAPIError",
    "_get_headers",
    "_retry_get",
]

BASE = "https://rest.coinapi.io/v1"


# ---------- Errors ----------
class CoinAPIError(RuntimeError):
    """Raised for any CoinAPI-related error"""

    pass


# ---------- Config / Headers ----------
def _get_headers() -> dict:
    """
    Load API key from config.yaml and return request headers.
    """
    config = load_config()
    try:
        key = config["providers"]["coinapi"]["api_key_env"]
    except Exception as e:
        raise CoinAPIError(f"Invalid config for CoinAPI: {e}")

    if not key:
        raise RuntimeError("CoinAPI key missing in config.yaml")

    return {"X-CoinAPI-Key": key}


# ---------- Utilities ----------
def _iso(ts: datetime) -> str:
    """Format datetime in ISO8601 with Z suffix"""
    return ts.replace(tzinfo=tz.utc).isoformat().replace("+00:00", "Z")


def _retry_get(
    url: str,
    params: dict | None = None,
    max_retry: int = 3,
    backoff: float = 0.8,
) -> requests.Response:
    """
    Retry GET requests with exponential backoff on transient errors.
    """
    last_err: Optional[Exception] = None
    for i in range(max_retry):
        try:
            resp = requests.get(url, headers=_get_headers(), params=params, timeout=15)

            if resp.status_code == 200:
                return resp

            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(backoff * (2**i))
                continue

            raise CoinAPIError(f"CoinAPI HTTP {resp.status_code}: {resp.text[:200]}")

        except Exception as e:
            last_err = e
            time.sleep(backoff * (2**i))

    raise CoinAPIError(f"CoinAPI request failed after retries: {last_err}")


# ---------- Public API ----------
def get_fx_rate(base: str, quote: str) -> float:
    url = f"{BASE}/exchangerate/{base.upper()}/{quote.upper()}"
    r = _retry_get(url)
    data = r.json()

    if "rate" not in data:
        raise CoinAPIError(f"Unexpected response: {data}")

    return float(data["rate"])


def get_ohlcv_latest(
    symbol_or_base: str,
    symbol_quote: str | None = None,
    period_id: str = "1MIN",
    limit: int = 100,
) -> list[dict]:
    def _call(symbol_id: str) -> list[dict]:
        url = f"{BASE}/ohlcv/{symbol_id}/latest"
        params = {"period_id": period_id, "limit": limit}
        r = _retry_get(url, params=params)
        data = r.json()

        if isinstance(data, dict) and data.get("error"):
            raise CoinAPIError(f"CoinAPI error: {data['error']}")

        return data

    if symbol_quote is None:
        return _call(symbol_or_base)

    base = symbol_or_base.upper()
    quote = symbol_quote.upper()
    candidates = [
        f"BITSTAMP_SPOT_{base}_{quote}",
        f"COINBASE_SPOT_{base}_{quote}",
        f"KRAKEN_SPOT_{base}_{quote}",
    ]

    last_err: Exception | None = None
    for sid in candidates:
        try:
            return _call(sid)
        except Exception as e:
            last_err = e
            continue

    raise CoinAPIError(
        f"OHLCV not found for {base}/{quote}. "
        f"Tried: {', '.join(candidates)}; last error: {last_err}"
    )


def ping() -> bool:
    try:
        _ = get_fx_rate("BTC", "USD")
        return True
    except Exception:
        return False
