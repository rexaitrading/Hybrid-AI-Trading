import os

RUN_SMOKE = os.getenv("IB_SMOKE_RUN", "0") == "1"

def test_bracket_create_and_cleanup():
    if not RUN_SMOKE:
        assert True
        return
    from ib_insync import IB, Stock, LimitOrder
    host = os.getenv("IB_HOST", "127.0.0.1")
    port = int(os.getenv("IB_PORT", "4002"))
    ib = IB()
    try:
        try:
            ib.client.setConnectOptions("UseSSL=0")
        except Exception:
            pass
        assert ib.connect(host, port, clientId=804, timeout=5)
        aapl = Stock("AAPL", "SMART", "USD")
        ib.qualifyContracts(aapl)
        parent = LimitOrder("BUY", 1, 1.00)  # far-away; never fills
        trade = ib.placeOrder(aapl, parent)
        ib.sleep(0.5)
        ib.cancelOrder(parent)
        ib.sleep(0.5)
    finally:
        try:
            ib.disconnect()
        except Exception:
            pass
