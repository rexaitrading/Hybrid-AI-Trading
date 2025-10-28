import os

RUN_SMOKE = os.getenv("IB_SMOKE_RUN", "0") == "1"


def test_ib_connect_smoke_strict():
    if not RUN_SMOKE:
        assert True
        return
    from ib_insync import IB

    host = os.getenv("IB_HOST", "127.0.0.1")
    port = int(os.getenv("IB_PORT", "4002"))
    ib = IB()
    try:
        try:
            ib.client.setConnectOptions("UseSSL=0")
        except Exception:
            pass
        assert ib.connect(host, port, clientId=802, timeout=5)
    finally:
        try:
            ib.disconnect()
        except Exception:
            pass
