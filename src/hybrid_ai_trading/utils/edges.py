from dataclasses import dataclass

from ib_insync import LimitOrder


@dataclass
class Signal:
    action: str = ""  # "BUY"/"SELL"
    order: object = None


def decide_signal(ticker):
    if not getattr(ticker, "bid", None) or not getattr(ticker, "ask", None):
        return Signal()
    mid = 0.5 * (ticker.bid + ticker.ask)
    spread = max(ticker.ask - ticker.bid, 0.01)
    if getattr(ticker, "last", None) and ticker.last > mid + 0.3 * spread:
        return Signal(
            "SELL", LimitOrder("SELL", 1, round(ticker.ask, 2), tif="GTC", outsideRth=True)
        )
    if getattr(ticker, "last", None) and ticker.last < mid - 0.3 * spread:
        return Signal("BUY", LimitOrder("BUY", 1, round(ticker.bid, 2), tif="GTC", outsideRth=True))
    return Signal()
