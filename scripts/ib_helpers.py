from ib_insync import *


def smart_stock(
    symbol: str, exch: str = "SMART", pxch: str = "NASDAQ", ccy: str = "USD"
):
    c = Stock(symbol, exch, ccy, primaryExchange=pxch)
    return c
