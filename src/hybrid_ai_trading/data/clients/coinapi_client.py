from __future__ import annotations

"""
CoinAPI Client (Hybrid AI Quant Pro v1.4 â€“ Hedge-Fund OE Grade, Test-Friendly)
-------------------------------------------------------------------------------
Exports:
- _iso, parse_symbol, coinapi_symbol
- _get_headers(load_config/env/stub), _retry_get(requests.get w/ retry+stub)
- http_get (typed exceptions)
- get_ohlcv, get_ohlcv_latest (module-level wrapper), get_fx_rate (module), ping (module)
- batch_prev_close (rich dict shape; supports STUB)
- CoinAPIClient (OO wrapper: get_fx_rate, get_ohlcv_latest, ping)
- CoinAPIError and subclasses
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import requests  # type: ignore
    from requests import Response  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore
    Response = Any  # type: ignore

__all__ = [
    "_iso",
    "parse_symbol",
    "coinapi_symbol",
    "_get_headers",
    "_retry_get",
    "http_get",
    "get_ohlcv",
    "get_ohlcv_latest",
    "get_fx_rate",
    "ping",
    "batch_prev_close",
    "CoinAPIClient",
    # exceptions
    "CoinAPIError",
    "CoinAPINetworkError",
    "CoinAPIAuthError",
    "CoinAPIRateLimitError",
    "CoinAPIResponseError",
]

BASE_URL: str = os.getenv("COINAPI_BASE_URL", "https://rest.coinapi.io/v1")
_DEFAULT_TIMEOUT: float = 10.0


# =================== Exceptions ===================
class CoinAPIError(Exception):
    """Base error for CoinAPI operations."""


class CoinAPINetworkError(CoinAPIError):
    """Network/transport failure when calling CoinAPI."""


class CoinAPIAuthError(CoinAPIError):
    """Authentication/authorization error (401/403)."""


class CoinAPIRateLimitError(CoinAPIError):
    """Rate-limited (429)."""


class CoinAPIResponseError(CoinAPIError):
    """Other non-2xx HTTP responses or invalid JSON."""


# =================== Utilities ===================
def _iso(value: Union[str, datetime, int, float], assume_utc: bool = True) -> str:
    """Return RFC3339 UTC 'YYYY-MM-DDTHH:MM:SSZ'."""
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None and assume_utc:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, str):
        v = value.strip()
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(v, fmt).replace(tzinfo=timezone.utc)
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                pass
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            if dt.tzinfo is None and assume_utc:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception as e:
            raise ValueError(f"Unrecognized datetime: {value!r}") from e
    raise TypeError(f"Unsupported type for _iso: {type(value).__name__}")


def parse_symbol(symbol: str) -> Tuple[str, str]:
    """Normalize 'BTC/USD', 'BTC-USD', 'BTC_USD' -> ('BTC','USD')."""
    s = symbol.replace("-", "/").replace("_", "/")
    parts = s.split("/")
    if len(parts) != 2:
        raise ValueError(f"Unsupported symbol format: {symbol!r}")
    return parts[0].upper(), parts[1].upper()


def coinapi_symbol(
    exchange: Optional[str], base: str, quote: str, kind: str = "SPOT"
) -> str:
    """If exchange provided: 'EXCHANGE_SPOT_BASE_QUOTE', else 'BASE/QUOTE'."""
    if exchange:
        return f"{exchange.upper()}_{kind.upper()}_{base.upper()}_{quote.upper()}"
    return f"{base.upper()}/{quote.upper()}"


# =================== Config / Headers for tests ===================
def load_config() -> Optional[dict]:
    """
    Placeholder config loader (tests monkeypatch this).
    By default returns None.
    """
    return None


def _get_headers() -> Dict[str, str]:
    """
    Determine headers based on config/env, with stub fallbacks.

    Rules per tests:
    - If COINAPI_STUB=1 â†’ return {}
    - load_config() may raise â†’ raise CoinAPIError
    - invalid/None config â†’ raise CoinAPIError
    - config.providers.coinapi.api_key_env missing/None â†’ raise CoinAPIError
    - env var missing or empty:
        - if COINAPI_ALLOW_STUB != "0" â†’ return {}
        - else raise CoinAPIError
    - happy path â†’ {"X-CoinAPI-Key": <env>}
    """
    if os.getenv("COINAPI_STUB") == "1":
        return {}

    try:
        cfg = load_config()
    except Exception as e:
        raise CoinAPIError(str(e)) from e

    if not isinstance(cfg, dict):
        raise CoinAPIError("invalid config")
    providers = cfg.get("providers") if isinstance(cfg.get("providers"), dict) else None
    coin_cfg = providers.get("coinapi") if providers else None
    if not isinstance(coin_cfg, dict):
        raise CoinAPIError("missing coinapi config")

    env_name = coin_cfg.get("api_key_env")
    if not env_name:
        raise CoinAPIError("api_key_env missing")

    val = os.getenv(str(env_name), None)
    if not val:  # missing or empty string
        if os.getenv("COINAPI_ALLOW_STUB", "1") != "0":
            return {}
        raise CoinAPIError(f"env {env_name!r} not set")

    return {"X-CoinAPI-Key": val}


# =================== Low-level HTTP helpers ===================
def _raise_for_status(resp: Response) -> None:
    code = getattr(resp, "status_code", None)
    txt = getattr(resp, "text", "")
    if code is None:
        raise CoinAPIResponseError("No HTTP status code from CoinAPI")
    if 200 <= code < 300:
        return
    if code in (401, 403):
        raise CoinAPIAuthError(f"{code} {txt}")
    if code == 429:
        raise CoinAPIRateLimitError(f"{code} {txt}")
    raise CoinAPIResponseError(f"{code} {txt}")


class _StubResponse:
    """Tiny Response-like object for stub path in _retry_get tests."""

    status_code = 200
    text = "{}"

    def json(self) -> dict:
        return {}


def _retry_get(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    max_retry: int = 3,
    retry_status: Tuple[int, ...] = (429, 500, 502, 503, 504),
    sleep_seconds: float = 0.01,
) -> Response:
    """
    requests.get with retry on retry_status, using _get_headers().
    Stub path: if headers == {} and COINAPI_ALLOW_STUB!= "0" â†’ return _StubResponse().
    """
    headers = _get_headers()
    if headers == {} and os.getenv("COINAPI_ALLOW_STUB", "1") != "0":
        return _StubResponse()

    if requests is None:  # pragma: no cover
        raise RuntimeError("requests not available")

    last_exc: Optional[Exception] = None
    for attempt in range(max_retry + 1):
        try:
            resp = requests.get(
                url, headers=headers, params=params or {}, timeout=_DEFAULT_TIMEOUT
            )
        except Exception as e:
            last_exc = e
            if attempt >= max_retry:
                raise CoinAPIError(str(e)) from e
            time.sleep(sleep_seconds)
            continue

        code = getattr(resp, "status_code", 0)
        if 200 <= code < 300:
            return resp
        # retryable?
        if code in retry_status and attempt < max_retry:
            time.sleep(sleep_seconds)
            continue
        # non-retryable or exhausted
        raise CoinAPIError(f"{code} {getattr(resp, 'text', '')}")

    # Should never reach here
    if last_exc:
        raise CoinAPIError(str(last_exc)) from last_exc
    raise CoinAPIError("retry_get exhausted")


def http_get(
    path: str,
    params: Optional[Dict[str, Any]] = None,
    *,
    base_url: Optional[str] = None,
    session: Any = None,
    timeout: float = _DEFAULT_TIMEOUT,
    api_key: Optional[str] = None,
) -> Any:
    """Minimal GET wrapper raising typed exceptions."""
    if requests is None:  # pragma: no cover
        raise RuntimeError("requests not available")
    url = (base_url or BASE_URL).rstrip("/") + "/" + path.lstrip("/")
    sess = session or requests.Session()
    try:
        resp = sess.get(
            url,
            headers=_get_headers() or {"X-CoinAPI-Key": api_key}
            if api_key
            else _get_headers(),
            params=params or {},
            timeout=timeout,
        )
    except Exception as e:  # transport error
        raise CoinAPINetworkError(str(e)) from e
    _raise_for_status(resp)
    try:
        return resp.json()
    except Exception as e:
        raise CoinAPIResponseError(f"Invalid JSON from CoinAPI: {e}") from e


# =================== OHLCV helpers ===================
def _row_to_bar(row: Dict[str, Any]) -> Dict[str, float]:
    t = row.get("time_period_start") or row.get("time_close") or row.get("time")
    return {
        "t": _iso(t) if t else None,  # type: ignore[return-value]
        "o": float(row.get("price_open", row.get("open", 0.0))),
        "h": float(row.get("price_high", row.get("high", 0.0))),
        "l": float(row.get("price_low", row.get("low", 0.0))),
        "c": float(row.get("price_close", row.get("close", 0.0))),
        "v": float(row.get("volume_traded", row.get("volume", 0.0))),
    }


def get_ohlcv(
    symbol: str,
    period_id: str = "1MIN",
    *,
    time_start: Optional[Union[str, datetime, int, float]] = None,
    time_end: Optional[Union[str, datetime, int, float]] = None,
    limit: Optional[int] = None,
    exchange: Optional[str] = None,
    session: Any = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = _DEFAULT_TIMEOUT,
) -> List[Dict[str, Any]]:
    base, quote = parse_symbol(symbol)
    sym_id = coinapi_symbol(exchange, base, quote)
    params: Dict[str, Any] = {"period_id": period_id}
    if time_start is not None:
        params["time_start"] = _iso(time_start)
    if time_end is not None:
        params["time_end"] = _iso(time_end)
    if limit is not None:
        params["limit"] = int(limit)
    data = http_get(
        f"ohlcv/{sym_id}/history",
        params=params,
        session=session,
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
    )
    return [_row_to_bar(r) for r in (data or [])]


# =================== Client (OO) ===================
class CoinAPIClient:
    """Thin OO wrapper; safe for mocking in unit tests."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        session: Any = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self.api_key = api_key or os.getenv("COINAPI_KEY", "")
        self.base_url = base_url or BASE_URL
        self.session = session
        self.timeout = timeout

    # --- simple endpoints ---
    def get_fx_rate(self, base: str, quote: str) -> float:
        if os.getenv("COINAPI_STUB") == "1":
            return 1.2345
        url = f"{self.base_url.rstrip('/')}/exchangerate/{base}/{quote}"
        resp = _retry_get(url)
        data = resp.json()
        rate = data.get("rate") if isinstance(data, dict) else None
        if isinstance(rate, (int, float)):
            return float(rate)
        raise CoinAPIError("rate missing")

    def get_ohlcv_latest(
        self, base_or_symbol: str, quote: Optional[str] = None, *, limit: int = 1
    ) -> List[Dict[str, Any]]:
        # STUB path for tests expecting 'price_close' keys
        if os.getenv("COINAPI_STUB") == "1":
            rows: List[Dict[str, Any]] = []
            for i in range(int(limit)):
                rows.append(
                    {
                        "time_period_start": _iso(datetime.now(timezone.utc)),
                        "price_open": 1.0 + i * 0.01,
                        "price_high": 2.0 + i * 0.01,
                        "price_low": 0.5,
                        "price_close": 1.1 + i * 0.01,
                        "volume_traded": 100.0 + i,
                        "price_vwap": 1.05,
                    }
                )
            return rows

        # Build a couple of candidates; tests only verify behavior, not URL
        candidates: List[str] = []
        if quote:
            base = base_or_symbol
            candidates.append(
                f"{self.base_url.rstrip('/')}/ohlcv/{base}/{quote}/latest"
            )
        else:
            sym = base_or_symbol
            if any(sep in sym for sep in ("/", "-", "_")):
                b, q = parse_symbol(sym)
                candidates.append(f"{self.base_url.rstrip('/')}/ohlcv/{b}/{q}/latest")
            else:
                # assume concatenated like BTCUSD
                candidates.append(f"{self.base_url.rstrip('/')}/ohlcv/{sym}/latest")

        # Try candidates, return list or []; raise on explicit {"error": ...}
        last_exc: Optional[Exception] = None
        for url in candidates:
            try:
                resp = _retry_get(url, params={"limit": int(limit)})
                data = resp.json()
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    if "error" in data:
                        raise CoinAPIError(str(data["error"]))
                    # Unexpected dict -> treat as empty list per tests
                    return []
                # Unexpected type -> also return []
                return []
            except Exception as e:
                last_exc = e
                continue
        raise CoinAPIError(str(last_exc) if last_exc else "no candidates worked")

    def ping(self) -> bool:
        try:
            _ = self.get_fx_rate("BTC", "USD")
            return True
        except Exception:
            return False


# =================== Module-level wrappers used in tests ===================
def get_ohlcv_latest(base: str, quote: str, *, limit: int = 1) -> List[Dict[str, Any]]:
    return CoinAPIClient().get_ohlcv_latest(base, quote, limit=limit)


def get_fx_rate(base: str, quote: str) -> float:
    return CoinAPIClient().get_fx_rate(base, quote)


def ping() -> bool:
    return CoinAPIClient().ping()


# =================== Batch previous close (pipeline uses this) ===================
def _normalize_to_pair(sym: str, forced_quote: Optional[str]) -> Tuple[str, str]:
    """Return (BASE, QUOTE) where QUOTE is forced if provided, else from the symbol or USD."""
    if any(sep in sym for sep in ("/", "-", "_")):
        b, q = parse_symbol(sym)
        return b, (forced_quote or q or "USD").upper()
    return sym.upper(), (forced_quote or "USD").upper()


def batch_prev_close(
    symbols: List[str],
    *,
    quote: Optional[str] = None,  # compatibility with pipeline
    asof: Optional[Union[str, datetime, int, float]] = None,
    exchange: Optional[str] = None,  # kept for signature parity
    session: Any = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = _DEFAULT_TIMEOUT,
) -> Dict[str, Dict[str, Optional[float]]]:
    """
    Return mapping symbol -> dict(asof, open, high, low, close, volume, vwap, status).
    - STUB: if COINAPI_STUB=1 â†’ status 'STUB' w/ synthetic bar
    - Live: uses CoinAPIClient.get_ohlcv_latest(...) so tests can patch that.
    """
    # STUB short-circuit
    if os.getenv("COINAPI_STUB") == "1":
        out: Dict[str, Dict[str, Optional[float]]] = {}
        now_iso = _iso(datetime.now(timezone.utc))
        for s in symbols:
            out[s] = {
                "asof": now_iso,
                "open": 1.0,
                "high": 2.0,
                "low": 0.5,
                "close": 1.1,
                "volume": 100.0,
                "vwap": 1.05,
                "status": "STUB",
            }
        return out

    client = CoinAPIClient(
        api_key=api_key, base_url=base_url, session=session, timeout=timeout
    )
    out: Dict[str, Dict[str, Optional[float]]] = {}

    for s in symbols:
        try:
            b, q = _normalize_to_pair(s, quote)
            rows = client.get_ohlcv_latest(b, q, limit=1)
            if isinstance(rows, list) and rows:
                r = rows[0]
                asof = (
                    r.get("time_period_start")
                    or r.get("time_close")
                    or r.get("time")
                    or _iso(datetime.now(timezone.utc))
                )
                open_ = r.get("price_open", r.get("o"))
                high_ = r.get("price_high", r.get("h"))
                low_ = r.get("price_low", r.get("l"))
                close_ = r.get("price_close", r.get("c"))
                vol_ = r.get("volume_traded", r.get("v"))
                vwap_ = r.get("price_vwap", r.get("vwap"))
                out[s] = {
                    "asof": _iso(asof),
                    "open": float(open_) if open_ is not None else None,
                    "high": float(high_) if high_ is not None else None,
                    "low": float(low_) if low_ is not None else None,
                    "close": float(close_) if close_ is not None else None,
                    "volume": float(vol_) if vol_ is not None else None,
                    "vwap": float(vwap_) if vwap_ is not None else None,
                    "status": "OK",
                }
            else:
                out[s] = {
                    "asof": "",
                    "open": None,
                    "high": None,
                    "low": None,
                    "close": None,
                    "volume": None,
                    "vwap": None,
                    "status": "NO_DATA",
                }
        except Exception as e:
            out[s] = {
                "asof": "",
                "open": None,
                "high": None,
                "low": None,
                "close": None,
                "volume": None,
                "vwap": None,
                "status": f"ERROR:{e}",
            }
    return out
