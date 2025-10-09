"""
Preflight IB Live Gate
Usage:
  $env:PYTHONPATH="src"
  python scripts/preflight_ib_live.py
"""

from hybrid_ai_trading.brokers.ib_client import IBClient, IBConfig


def main():
    cli = IBClient(IBConfig())
    with cli.session():
        ver, now = cli.server_info()
        print(f"Connected. Server version={ver}  Time={now}")

        summary = cli.account_summary()
        for k in ("TotalCashValue", "BuyingPower", "NetLiquidation"):
            v = summary.get(k)
            print(f"{k}: {v[0]} {v[1]}" if v else f"{k}: <missing>")

        ok, errs = cli.ensure_realtime_equity_entitlement("AAPL")
        if not ok:
            print("❌ Real-time equity entitlement not confirmed.")
            if errs:
                for code, msg in errs:
                    print(f"Error {code}: {msg}")
            raise SystemExit(2)
        else:
            print("✅ Real-time entitlement check passed (AAPL snapshot had values).")

        wi = cli.what_if_market_buy("AAPL", 1)
        print("What-If:", wi)


if __name__ == "__main__":
    main()
