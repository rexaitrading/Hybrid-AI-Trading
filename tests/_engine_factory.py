from typing import Any, Dict, Optional

from hybrid_ai_trading.trade_engine import TradeEngine


def make_engine(config: Optional[Dict[str, Any]] = None) -> TradeEngine:
    # minimal default config; engine defaults are robust
    return TradeEngine(config or {})


def call_signal(
    engine: TradeEngine,
    symbol: str,
    signal: str,
    price: float = None,
    size: int = None,
    algo: str = None,
) -> Dict[str, Any]:
    return engine.process_signal(symbol, signal, price=price, size=size, algo=algo)


def find(*args, **kwargs) -> Dict[str, Any]:
    # provide a benign stub; tests that rely on it can override
    return {}
