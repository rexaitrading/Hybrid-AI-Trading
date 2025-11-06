from __future__ import annotations

import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List

__all__ = ["load_providers", "get_price", "get_price_retry", "get_prices"]

# tiny in-process cache to reduce API traffic during loops
_CACHE: Dict[str, Any] = {}
_CACHE_TTL_SEC = float(os.getenv("HAT_CACHE_TTL_SEC", "3.0") or 0)
HAT_NO_CACHE = os.getenv("HAT_NO_CACHE", "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


def _expand_env(s: str) -> str:
    """
    Expands: ${VAR}, ${ENV:VAR}, ${VAR:-default}, ${ENV:VAR:-default}
    """
    if not isinstance(s, str):
        return s or ""
    pat = re.compile(r"\$\{(?:(ENV:)?([A-Za-z_][A-Za-z0-9_]*))(?:[:-]([^\}]*))?\}")

    def repl(m):
        _, var, default = m.groups()
        return os.environ.get(var, default or "")

    return pat.sub(repl, s)


def load_providers(path: str = "config/providers.yaml") -> Dict[str, Any]:
    p = pathlib.Path(path)
    if not p.exists():
        return {}
    try:
        import yaml  # optional dep in this repo
    except Exception:
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    def expand_obj(x):
        if isinstance(x, str):
            return _expand_env(x)
        if isinstance(x, dict):
            return {k: expand_obj(v) for k, v in x.items()}
        if isinstance(x, list):
            return [expand_obj(v) for v in x]
        return x

    return expand_obj(data or {})


def _http_json(url: str, headers=None, timeout=5):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {e}"}


def _is_crypto_symbol(symbol: str) -> bool:
    s = (symbol or "").upper().strip()
    if any(x in s for x in ("/", "-", "_")):
        return True
    if re.match(r"^[A-Z0-9]{2,12}(USDT|USDC|USD|EUR|CAD)$", s):
        return True
    if s in (
        "BTC",
        "XBT",
        "ETH",
        "SOL",
        "ADA",
        "XRP",
        "DOGE",
        "LTC",
        "BNB",
        "DOT",
        "MATIC",
    ):
        return True
    return False


def _is_fx_symbol(symbol: str) -> bool:
    s = (symbol or "").upper().strip()
    if re.match(r"^[A-Z]{6}$", s) and s.endswith(
        ("USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "NZD", "CNH")
    ):
        return True
    if any(x in s for x in ("/", "-", "_")):
        parts = re.split(r"[/\-_]", s)
        if len(parts) == 2 and len(parts[0]) == 3 and len(parts[1]) == 3:
            return True
    return False


def get_price(symbol: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Routing rules (best-effort, safe on missing deps):
      - Metals: XAUUSD/XAGUSD -> CoinAPI (exchangerate)
      - FX: CoinAPI first, Polygon fallback
      - Crypto: CoinAPI -> Kraken -> CryptoCompare
      - Equity/other: Polygon -> CoinAPI fallback
      - CL1!: prefer Polygon only
    Cache controlled by HAT_NO_CACHE/HAT_CACHE_TTL_SEC.
    """
    now = time.time()
    s = (symbol or "").strip()
    if not s:
        return {
            "symbol": symbol,
            "price": None,
            "source": "none",
            "reason": "empty_symbol",
        }

    if not HAT_NO_CACHE and s in _CACHE:
        ts, val = _CACHE.get(s, (0, None))
        if now - ts <= _CACHE_TTL_SEC:
            return val

    providers = cfg.get("providers", {}) if isinstance(cfg, dict) else {}
    result = {"symbol": s, "price": None, "source": "none", "reason": "no_clients"}

    def _try_coinapi_fx(pair: str):
        try:
            from hybrid_ai_trading.data.clients.coinapi_client import (
                Client as Coin,
            )  # repo path variant
        except Exception:
            try:
                from hybrid_ai_trading.data_clients.coinapi_client import (
                    Client as Coin,
                )  # legacy path
            except Exception:
                return None
        try:
            cli = Coin(**(providers.get("coinapi", {}) or {}))
            r = cli.exchangerate(pair)
            px = float(r.get("rate"))
            return {"symbol": s, "price": px, "source": "coinapi"}
        except Exception:
            return None

    def _try_polygon_equity(sym: str):
        try:
            from hybrid_ai_trading.data.clients.polygon_client import Client as Poly
        except Exception:
            try:
                from hybrid_ai_trading.data_clients.polygon_client import Client as Poly
            except Exception:
                return None
        try:
            cli = Poly(**(providers.get("polygon", {}) or {}))
            px = float(cli.last_price(sym))
            return {"symbol": s, "price": px, "source": "polygon"}
        except Exception:
            return None

    def _try_kraken_crypto(sym: str):
        try:
            from hybrid_ai_trading.data.clients.kraken_client import Client as Kr
        except Exception:
            try:
                from hybrid_ai_trading.data_clients.kraken_client import Client as Kr
            except Exception:
                return None
        try:
            cli = Kr(**(providers.get("kraken", {}) or {}))
            px = float(cli.last_price(sym))
            return {"symbol": s, "price": px, "source": "kraken"}
        except Exception:
            return None

    def _try_cryptocompare(sym: str):
        try:
            from hybrid_ai_trading.data.clients.cryptocompare_client import Client as CC
        except Exception:
            try:
                from hybrid_ai_trading.data_clients.cryptocompare_client import (
                    Client as CC,
                )
            except Exception:
                return None
        try:
            cli = CC(**(providers.get("cryptocompare", {}) or {}))
            px = float(cli.last_price(sym))
            return {"symbol": s, "price": px, "source": "cryptocompare"}
        except Exception:
            return None

    # Metals
    if s in ("XAUUSD", "XAGUSD"):
        out = _try_coinapi_fx(s)
        if out:
            result = out

    # FX
    elif _is_fx_symbol(s):
        out = _try_coinapi_fx(s)
        if not out:
            out = _try_polygon_equity(f"C:{s}")  # polygon fx instrument code
        if out:
            result = out

    # Crypto
    elif _is_crypto_symbol(s):
        out = _try_coinapi_fx(s)  # CoinAPI crypto pairs supported via exchangerate
        if not out:
            out = _try_kraken_crypto(s)
        if not out:
            out = _try_cryptocompare(s)
        if out:
            result = out

    # Equity / other
    else:
        if s.upper() == "CL1!":
            out = _try_polygon_equity(s)
        else:
            out = _try_polygon_equity(s) or _try_coinapi_fx(s)
        if out:
            result = out

    # Cache
    _CACHE[s] = (now, result)
    return result


def get_price_retry(
    symbol: str, cfg: Dict[str, Any], retries: int = 2
) -> Dict[str, Any]:
    last = None
    for _ in range(max(0, retries) + 1):
        last = get_price(symbol, cfg)
        if last and last.get("price"):
            return last
    return last or {
        "symbol": symbol,
        "price": None,
        "source": "none",
        "reason": "retry_failed",
    }


def get_prices(symbols: List[str], cfg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for sym in list(symbols or []):
        out[sym] = get_price(sym, cfg)
    return out
