from hybrid_ai_trading.utils.ib_conn import ib_session
from ib_insync import *

with ib_session(timeout=30, market_data_type=3) as ib:
    c = Stock("AAPL", "SMART", "USD")
    ib.qualifyContracts(c)
    t = ib.reqMktData(c, "", False, False)
    ib.sleep(2.5)
    print("AAPL quote:", t.bid, t.ask, t.last)
    st = ib.whatIfOrder(c, LimitOrder("BUY", 1, 0.01, whatIf=True))
    print("whatIf:", st.status, getattr(st, "initMarginChange", None))
    print(
        "positions:",
        [(p.contract.symbol, p.position, p.avgCost) for p in ib.positions()],
    )
    print(
        "openOrders:",
        [
            (o.order.permId, o.order.action, o.order.totalQuantity, o.orderState.status)
            for o in ib.openOrders()
        ],
    )
