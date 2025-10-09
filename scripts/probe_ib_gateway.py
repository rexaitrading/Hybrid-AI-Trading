"""
Probe IB Connection (v3.0 – Env Override + Summary + Market Snapshot + What-If)
-------------------------------------------------------------------------------
- Loads .env with override=True so it beats OS env vars
- Connects to host/port/clientId from env
- Prints server version and current time
- Prints account summary (cash, buying power, net liquidation)
- Requests a market data snapshot for AAPL (delayed if no RT subscription)
- Runs a What-If market order (safe, no execution)
- Auto-fallback to localhost:4002 if .env fails
"""

import os
from ib_insync import IB, Stock, MarketOrder
try:
    from dotenv import load_dotenv, find_dotenv
except Exception:
    load_dotenv = None
    find_dotenv = None


def load_env():
    if load_dotenv and find_dotenv:
        path = find_dotenv(usecwd=True)
        load_dotenv(dotenv_path=path, override=True)
        print(f"Loaded .env from: {path or '(not found)'}")
    else:
        print("python-dotenv not available; using existing environment only.")


def get_cfg():
    host = os.getenv("IB_GATEWAY_HOST", "localhost")
    port = int(os.getenv("IB_GATEWAY_PORT", "4002"))
    cid = int(os.getenv("IB_CLIENT_ID", "7"))
    return host, port, cid


def try_connect(host, port, cid, label="primary"):
    ib = IB()
    print(f"Trying ({label}) {host}:{port} clientId={cid} ...")
    try:
        ib.connect(host, port, clientId=cid)
        if ib.isConnected():
            print("✅ Connected successfully!")
            print("Server version:", ib.client.serverVersion())
            print("TWS/Gateway time:", ib.reqCurrentTime())

            # --- Account summary ---
            summary = ib.accountSummary()
            for entry in summary:
                if entry.tag in ("TotalCashValue", "BuyingPower", "NetLiquidation"):
                    print(f"{entry.tag}: {entry.value} {entry.currency}")

            # --- Market data snapshot ---
            ib.reqMarketDataType(4)  # delayed-frozen if no subscription
            contract = Stock("AAPL", "SMART", "USD")
            ticker = ib.reqMktData(contract, "", snapshot=True)
            ib.sleep(2.0)  # wait for snapshot
            print(f"AAPL snapshot -> last: {ticker.last} bid: {ticker.bid} ask: {ticker.ask}")

            # --- What-If order (no real trade) ---
            order = MarketOrder("BUY", 1)
            state = ib.whatIfOrder(contract, order)
            print("What-If order status:", state.status)
            print("Init margin before:", state.initMarginBefore,
                  "Change:", state.initMarginChange,
                  "After:", state.initMarginAfter)
            print("Commission estimate:", state.commission)

            return True
        else:
            print("❌ Connected returned False.")
            return False
    except Exception as e:
        print(f"❌ API connection failed ({label}): {repr(e)}")
        return False
    finally:
        ib.disconnect()


def main():
    load_env()
    host, port, cid = get_cfg()

    if host == "127.0.0.1":
        print("⚠️ Host is 127.0.0.1; prefer 'localhost' so IPv6 ::1 works.")

    ok = try_connect(host, port, cid, label="env")
    if ok:
        return

    # Fallback only if env wasn’t already the known-good combo
    if not (host in ("localhost", "::1") and port == 4002):
        print("🔁 Trying fallback to localhost:4002 (Gateway paper, IPv6-friendly)...")
        try_connect("localhost", 4002, cid if cid else 7, label="fallback")


if __name__ == "__main__":
    main()
