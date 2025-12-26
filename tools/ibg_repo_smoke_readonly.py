"""
Read-only IB Gateway smoke test (repo-native).
- Connect via hybrid_ai_trading.brokers.ib_client.IBClient (ib_insync)
- Print server info + key account summary
- Disconnect cleanly
No orders. Safe to run any time.
"""

from hybrid_ai_trading.brokers.ib_client import IBClient

def main() -> int:
    c = IBClient()
    c.connect()
    print("SERVER", c.server_info())
    print("ACCT", c.account_summary())
    c.disconnect()
    print("OK_DISCONNECTED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
