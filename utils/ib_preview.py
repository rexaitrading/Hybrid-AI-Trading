from typing import Literal, Dict, Any, Optional
from ib_insync import IB, Stock, MarketOrder, LimitOrder

def _to_f(x):
    try: return float(str(x))
    except: return None

def _ok(v): return v is not None and v < 1e300

def _pick(st, *names):
    for n in names:
        v = _to_f(getattr(st, n, None))
        if _ok(v): return v
    return None

def whatif_preview(
    symbol: str,
    qty: int = 1,
    side: Literal["BUY","SELL"] = "BUY",
    order_type: Literal["MARKET","LIMIT"] = "MARKET",
    limit_price: Optional[float] = None,
    host: str = "127.0.0.1", port: int = 7497, client_id: int = 2001,
    exchange: str = "SMART", currency: str = "USD", primary: str = "NASDAQ",
    mkt_data_type: int = 3,   # 1=RT, 3=Delayed
) -> Dict[str, Any]:
    ib = IB()
    ib.connect(host, port, clientId=client_id, timeout=30)
    ib.reqMarketDataType(mkt_data_type)

    acct = ib.managedAccounts()[0]
    c = Stock(symbol, exchange, currency, primaryExchange=primary)
    ib.qualifyContracts(c)

    if order_type == "MARKET":
        o = MarketOrder(side, qty, account=acct)
    else:
        assert limit_price is not None, "limit_price required for LIMIT"
        o = LimitOrder(side, qty, limit_price, account=acct)

    st = ib.whatIfOrder(c, o)

    init  = _pick(st,"initMargin","initMarginAfter","initMarginChange")
    maint = _pick(st,"maintMargin","maintMarginAfter","maintMarginChange")
    ewl   = _pick(st,"equityWithLoan","equityWithLoanAfter","equityWithLoanChange")
    comm  = _to_f(getattr(st,"commission",None))
    comm_ccy = getattr(st,"commissionCurrency","")

    out = {
        "account": acct,
        "symbol": symbol,
        "side": side,
        "orderType": order_type,
        "qty": qty,
        "limitPrice": limit_price,
        "status": getattr(st,"status",None),
        "initMargin_total": init,
        "maintMargin_total": maint,
        "initMargin_perUnit": (init/qty if _ok(init) and qty>0 else None),
        "maintMargin_perUnit": (maint/qty if _ok(maint) and qty>0 else None),
        "equityWithLoan": ewl,
        "commission": comm,
        "commissionCurrency": comm_ccy,
    }
    ib.disconnect()
    return out