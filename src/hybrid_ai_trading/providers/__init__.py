def load_providers(path: str):
    from .price import load_providers as _lp

    return _lp(path)


def get_price(symbol: str, cfg: dict):
    from .price import get_price as _gp

    return _gp(symbol, cfg)


__all__ = ["get_price", "load_providers"]
