import os, re, pathlib, json
from typing import Any, Dict
import urllib.request, urllib.error

__all__ = ["load_providers", "get_price", "get_price_retry"]

# tiny in-process cache to reduce API traffic during loops
_CACHE: dict = {}
_CACHE_TTL_SEC = float(os.getenv("HAT_CACHE_TTL_SEC", "3.0") or 0)
HAT_NO_CACHE = os.getenv("HAT_NO_CACHE", "").strip().lower() in ("1","true","yes","on")

def _expand_env(s: str) -> str:
    """
    Expands:
      ${VAR}, ${ENV:VAR}, ${VAR:-default}, ${ENV:VAR:-default}
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
    import yaml
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    def expand_obj(x):
        if isinstance(x, str): return _expand_env(x)
        if isinstance(x, dict): return {k: expand_obj(v) for k, v in x.items()}
        if isinstance(x, list): return [expand_obj(v) for v in x]
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
    import re
    s = (symbol or "").upper().strip()
    # obvious separators
    if any(x in s for x in ("/","-","_")):
        return True
    # concatenated pairs: BTCUSD, ETHUSDT, SOLUSDC, etc.
    if re.match(r"^[A-Z0-9]{2,12}(USDT|USDC|USD|EUR|CAD)$", s):
        return True
    # common crypto bases
    if s in ("BTC","XBT","ETH","SOL","ADA","XRP","DOGE","LTC","BNB","DOT","MATIC"):
        return True
    return False

def get_price(symbol: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Route by asset class:
      - Equities -> polygon
      - Crypto   -> coinapi (normalized pairs) with kraken fallback
    Try multiple, soft-skip 'not_implemented', return first price.
    Apply in-process cache per symbol (ttl from env; disable via HAT_NO_CACHE).
    """
    import time
    now = time.time()
    if not HAT_NO_CACHE and symbol in _CACHE:
        ts, val = _CACHE.get(symbol, (0, None))
        if now - ts <= _CACHE_TTL_SEC:
            return val

    result = {"symbol": symbol, "price": None, "source": "none", "reason": "no_clients"}
    providers = cfg.get("providers", {}) if isinstance(cfg, dict) else {}

    constructed = []
    is_crypto = _is_crypto_symbol(symbol)

    if is_crypto:
        # coinapi first for crypto
        try:
            from hybrid_ai_trading.data_clients.coinapi_client import Client as Coin
            ccfg = dict(providers.get("coinapi", {}) or {})
            constructed.append(("coinapi", Coin(**ccfg)))
        except Exception:
            pass
        # kraken as fallback (public endpoint)
        try:
            from hybrid_ai_trading.data_clients.kraken_client import Client as Krk
            kcfg = dict(providers.get("kraken", {}) or {})
            constructed.append(("kraken", Krk(**kcfg)))
        except Exception:
            pass
    else:
        # polygon for equities
        try:
            from hybrid_ai_trading.data_clients.polygon_client import Client as Poly
            pcfg = dict(providers.get("polygon", {}) or {})
            constructed.append(("polygon", Poly(**pcfg)))
        except Exception:
            pass
        # coinapi fallback (rare for equities)
        try:
            from hybrid_ai_trading.data_clients.coinapi_client import Client as Coin
            ccfg = dict(providers.get("coinapi", {}) or {})
            constructed.append(("coinapi", Coin(**ccfg)))
        except Exception:
            pass

    if not constructed:
        out = {"symbol": symbol, "price": None, "source": "none", "reason": "no_clients_constructed"}
        if not HAT_NO_CACHE: _CACHE[symbol] = (now, out)
        return out

    last = result
    for name, client in constructed:
        try:
            q = client.last_quote(symbol)
            if isinstance(q, dict):
                if q.get("reason") == "not_implemented" and q.get("price") is None:
                    last = {"symbol": symbol, "price": None, "source": name, "reason": "not_implemented"}
                    continue
                if q.get("price") is not None:
                    q.setdefault("source", name)
                    if not HAT_NO_CACHE: _CACHE[symbol] = (now, q)
                    return q
                last = {"symbol": symbol, "price": None, "source": name, "reason": q.get("reason", "no_price")}
            else:
                last = {"symbol": symbol, "price": None, "source": name, "reason": "bad_response"}
        except Exception as e:
            last = {"symbol": symbol, "price": None, "source": name, "reason": f"error:{type(e).__name__}"}
    if not HAT_NO_CACHE: _CACHE[symbol] = (now, last)
    return last

def get_price_retry(symbol, cfg, attempts=3, delay=0.4):
    """Retry get_price with basic backoff."""
    import time
    last = None
    for i in range(max(1, attempts)):
        last = get_price(symbol, cfg)
        if last.get("price") is not None:
            return last
        time.sleep(delay * (1 + i))
    return last or {"symbol": symbol, "price": None, "source": "none", "reason": "retry_exhausted"}