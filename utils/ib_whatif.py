from ib_insync import IB, Stock, MarketOrder

def whatif_margins(
    host="127.0.0.1", port=7497, client_id=2001,
    symbol="AAPL", exchange="SMART", currency="USD",
    primary="NASDAQ"
):
    def to_f(x):
        try: return float(str(x))
        except: return None
    def ok(v): return v is not None and v < 1e300
    def pick(st,*names):
        for n in names:
            v = to_f(getattr(st, n, None))
            if ok(v): return v
        return None

    ib = IB()
    ib.connect(host, port, clientId=client_id, timeout=30)

    acct = ib.managedAccounts()[0]
    c = Stock(symbol, exchange, currency, primaryExchange=primary)
    ib.qualifyContracts(c)
    ib.reqMarketDataType(3)  # force delayed quotes

    st = ib.whatIfOrder(c, MarketOrder("BUY", 1, account=acct))

    out = {
        "account": acct,
        "symbol": symbol,
        "status": getattr(st, "status", None),
        "commission": to_f(getattr(st, "commission", None)),
        "commissionCurrency": getattr(st, "commissionCurrency", ""),
        "initMargin": pick(st, "initMargin","initMarginAfter","initMarginChange"),
        "maintMargin": pick(st, "maintMargin","maintMarginAfter","maintMarginChange"),
        "equityWithLoan": pick(st, "equityWithLoan","equityWithLoanAfter","equityWithLoanChange"),
    }
    ib.disconnect()
    return out