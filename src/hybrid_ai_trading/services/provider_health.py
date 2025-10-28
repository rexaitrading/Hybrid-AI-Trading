from time import perf_counter
from typing import Any, Dict, List

from fastapi import FastAPI

from hybrid_ai_trading.data_clients.coinapi_client import Client as Coin
from hybrid_ai_trading.data_clients.cryptocompare_client import Client as CC
from hybrid_ai_trading.data_clients.kraken_client import Client as Krk

# direct clients
from hybrid_ai_trading.data_clients.polygon_client import Client as Poly
from hybrid_ai_trading.utils.providers import load_providers

app = FastAPI(title="Provider Health")

# (provider_name, symbol, ctor)
CHECKS = [
    ("polygon", "AAPL", "polygon"),
    ("coinapi", "BTCUSD", "coinapi"),
    ("kraken", "BTC/USDT", "kraken"),
    ("cryptocompare", "BTCUSDT", "cryptocompare"),
]


def _make_client(name: str, cfg: Dict[str, Any]):
    ps = cfg.get("providers") or {}
    if name == "polygon":
        return Poly(**(ps.get("polygon") or {}))
    if name == "coinapi":
        return Coin(**(ps.get("coinapi") or {}))
    if name == "kraken":
        return Krk(**(ps.get("kraken") or {}))
    if name == "cryptocompare":
        return CC(**(ps.get("cryptocompare") or {}))
    raise ValueError(f"unknown provider {name}")


@app.get("/health/providers")
def health_providers(providers: List[str] = None) -> Dict[str, Any]:
    cfg = load_providers("config/providers.yaml")
    checks = [c for c in CHECKS if (not providers or c[0] in providers)]
    out = []
    for prov, sym, key in checks:
        t0 = perf_counter()
        try:
            cl = _make_client(key, cfg)
            r = cl.last_quote(sym)
            lat = (perf_counter() - t0) * 1000.0
            ok = isinstance(r, dict) and isinstance(r.get("price"), (int, float))
            out.append(
                {"provider": prov, "symbol": sym, "lat_ms": round(lat, 2), "ok": ok, "resp": r}
            )
        except Exception as e:
            lat = (perf_counter() - t0) * 1000.0
            out.append(
                {
                    "provider": prov,
                    "symbol": sym,
                    "lat_ms": round(lat, 2),
                    "ok": False,
                    "error": f"{type(e).__name__}: {e}",
                }
            )
    return {"checks": out}
