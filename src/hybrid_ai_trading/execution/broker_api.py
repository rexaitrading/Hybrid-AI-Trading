def place_limit(symbol: str, side: str, qty: int, limit_price: float):
    """
    Places a limit order via router (IBKR primary -> Alpaca fallback).
    Returns a dict with broker/status/resp.
    """
    return _router.place_limit(symbol, side, qty, limit_price)
