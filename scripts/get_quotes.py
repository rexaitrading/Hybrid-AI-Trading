# get_quotes.py  —  UTF-8 (no BOM)
import sys, argparse, json
from datetime import datetime, timezone
from ib_insync import IB, Stock

def main():
    ap = argparse.ArgumentParser(description="IB quotes + small account snapshot")
    ap.add_argument('symbols', nargs='*', help='Symbols, e.g. AAPL MSFT NVDA')
    ap.add_argument('--port', type=int, default=4002, help='API port (default 4002)')
    ap.add_argument('--host', default='127.0.0.1', help='Host (default 127.0.0.1)')
    ap.add_argument('--clientId', type=int, default=101, help='Client ID (default 101)')
    ap.add_argument('--mdType', type=int, default=3, choices=[1,2,3,4],
                    help='Market data type: 1=live,2=frozen,3=delayed,4=delayed_frozen (default 3)')
    ap.add_argument('--snapshot', action='store_true', help='Request snapshot quotes (permissions required)')
    ap.add_argument('--primary', default='NASDAQ', help='Primary exchange hint for US stocks (default NASDAQ)')
    ap.add_argument('--json', action='store_true', help='Emit JSON (machine-readable)')
    args = ap.parse_args()

    # default symbol for demo if none provided
    syms = args.symbols or ['AAPL']

    ib = IB()
    try:
        ib.connect(args.host, args.port, clientId=args.clientId, timeout=30)
        if not ib.isConnected():
            print("ERROR: Could not connect to IB API", file=sys.stderr)
            sys.exit(2)

        # Set market data mode
        ib.reqMarketDataType(args.mdType)

        # Build contracts
        contracts = [Stock(s, 'SMART', 'USD', primaryExchange=args.primary) for s in syms]

        # Request quotes
        ticks = []
        for c in contracts:
            t = ib.reqMktData(c, '', args.snapshot, False)
            ticks.append((c, t))

        # Give IB a second or two to deliver ticks
        ib.sleep(2.5)

        # Small account snapshot
        acctTags = {'NetLiquidation','AvailableFunds','BuyingPower','TotalCashValue','GrossPositionValue'}
        acct = {}
        try:
            for s in ib.accountSummary():
                if s.tag in acctTags:
                    acct[s.tag] = {'value': s.value, 'ccy': s.currency}
        except Exception:
            acct = {}

        now = datetime.now(timezone.utc).isoformat()
        out = {
            'ts': now,
            'connected': ib.isConnected(),
            'serverVersion': ib.client.serverVersion(),
            'mdType': args.mdType,
            'quotes': []
        }

        for c, t in ticks:
            out['quotes'].append({
                'symbol': c.symbol,
                'bid': t.bid,
                'ask': t.ask,
                'last': t.last,
                'close': t.close,
                'volume': t.volume,
                'halted': t.halted,
                'marketDataWarning': t.marketDataType
            })
            # cancel if streaming
            if not args.snapshot:
                ib.cancelMktData(c)

        out['account'] = acct

        if args.json:
            print(json.dumps(out, indent=2))
        else:
            print(f"[{now}] connected={out['connected']} serverVersion={out['serverVersion']} mdType={out['mdType']}")
            for q in out['quotes']:
                print(f"{q['symbol']:>6}  bid={q['bid']}  ask={q['ask']}  last={q['last']}  close={q['close']}  vol={q['volume']}")
            if acct:
                print("Account:", ", ".join(f"{k}={v['value']} {v['ccy']}" for k,v in acct.items()))
    finally:
        if ib.isConnected():
            ib.disconnect()

if __name__ == '__main__':
    main()