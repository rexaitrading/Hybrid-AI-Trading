from __future__ import annotations

import argparse
import sys
from typing import Optional

from ib_insync import LimitOrder, Stock

from .ib_conn import DEFAULT_CLIENT_ID, DEFAULT_HOST, DEFAULT_PORT, ib_session
from .structured_log import get_logger, setup_logging

log = get_logger("hybrid_ai_trading.cli")


def _add_common(p):
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--client-id", type=int, default=DEFAULT_CLIENT_ID)
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument(
        "--mdt", type=int, default=3, help="1=live,2=frozen,3=delayed,4=delayed-frozen"
    )
    p.add_argument(
        "--log", action="store_true", help="Enable ib_insync wire logs to console"
    )
    p.add_argument(
        "--log-file", default=None, help="Path to structured log file (JSON lines)."
    )
    p.add_argument("--log-level", default="INFO", help="DEBUG/INFO/WARN/ERROR")
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON logs (default on when --log-file given)",
    )


def _setup_cli_logging(args):
    json_on = args.json or bool(args.log_file)
    setup_logging(level=args.log_level, logfile=args.log_file, json_output=json_on)


def cmd_ping(args):
    _setup_cli_logging(args)
    with ib_session(
        host=args.host,
        port=args.port,
        client_id=args.client_id,
        timeout=args.timeout,
        market_data_type=args.mdt,
        log=args.log,
    ) as ib:
        print("Connected:", ib.isConnected())
        print("serverTime:", ib.reqCurrentTime())
        print("accounts:", ib.managedAccounts())
        # version info (best-effort)
        vers = {}
        try:
            cv = getattr(getattr(ib, "client", None), "clientVersion", None)
            vers["client"] = cv() if callable(cv) else None
        except Exception:
            pass
        try:
            sv = getattr(getattr(ib, "client", None), "serverVersion", None)
            vers["server"] = sv() if callable(sv) else None
        except Exception:
            pass
        if any(v is not None for v in vers.values()):
            print("versions:", vers)


def _stock(sym, exch="SMART", cur="USD"):
    return Stock(sym, exch, cur)


def cmd_quote(args):
    _setup_cli_logging(args)
    with ib_session(
        host=args.host,
        port=args.port,
        client_id=args.client_id,
        timeout=args.timeout,
        market_data_type=args.mdt,
        log=args.log,
    ) as ib:
        c = _stock(args.symbol, args.exchange, args.currency)
        ib.qualifyContracts(c)
        t = ib.reqMktData(c, "", False, False)
        ib.sleep(max(1.5, args.wait))
        print(f"{args.symbol} quote:", t.bid, t.ask, t.last)


def cmd_whatif(args):
    _setup_cli_logging(args)
    with ib_session(
        host=args.host,
        port=args.port,
        client_id=args.client_id,
        timeout=args.timeout,
        market_data_type=args.mdt,
        log=args.log,
    ) as ib:
        c = _stock(args.symbol, args.exchange, args.currency)
        ib.qualifyContracts(c)
        o = LimitOrder(args.side.upper(), args.qty, float(args.limit), whatIf=True)
        st = ib.whatIfOrder(c, o)
        print("whatIf:", st.status, getattr(st, "initMarginChange", None))


def cmd_positions(args):
    _setup_cli_logging(args)
    with ib_session(
        host=args.host,
        port=args.port,
        client_id=args.client_id,
        timeout=args.timeout,
        market_data_type=args.mdt,
        log=args.log,
    ) as ib:
        pos = [(p.contract.symbol, p.position, p.avgCost) for p in ib.positions()]
        print("positions:", pos)


def cmd_open_orders(args):
    _setup_cli_logging(args)
    with ib_session(
        host=args.host,
        port=args.port,
        client_id=args.client_id,
        timeout=args.timeout,
        market_data_type=args.mdt,
        log=args.log,
    ) as ib:
        ops = [
            (o.order.permId, o.order.action, o.order.totalQuantity, o.orderState.status)
            for o in ib.openOrders()
        ]
        print("openOrders:", ops)


def cmd_health(args):
    _setup_cli_logging(args)
    with ib_session(
        host=args.host,
        port=args.port,
        client_id=args.client_id,
        timeout=args.timeout,
        market_data_type=args.mdt,
        log=args.log,
    ) as ib:
        print("Connected:", ib.isConnected())
        print("serverTime:", ib.reqCurrentTime())
        print("accounts:", ib.managedAccounts())
        c = _stock("AAPL", "SMART", "USD")
        ib.qualifyContracts(c)
        t = ib.reqMktData(c, "", False, False)
        ib.sleep(2.0)
        print("AAPL quote:", t.bid, t.ask, t.last)
        st = ib.whatIfOrder(c, LimitOrder("BUY", 1, 0.01, whatIf=True))
        print("whatIf:", st.status, getattr(st, "initMarginChange", None))


def main(argv: Optional[list[str]] = None):
    parser = argparse.ArgumentParser(
        prog="ib", description="Hybrid AI Quant Pro â€” IBKR CLI"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ping = sub.add_parser("ping", help="Test handshake and print server/account info")
    _add_common(p_ping)
    p_ping.set_defaults(func=cmd_ping)

    p_quote = sub.add_parser("quote", help="Get a quick quote (bid/ask/last)")
    p_quote.add_argument("symbol")
    p_quote.add_argument("--exchange", default="SMART")
    p_quote.add_argument("--currency", default="USD")
    p_quote.add_argument("--wait", type=float, default=2.0)
    _add_common(p_quote)
    p_quote.set_defaults(func=cmd_quote)

    p_wi = sub.add_parser("whatif", help="Simulate a limit order (no transmit)")
    p_wi.add_argument("symbol")
    p_wi.add_argument("--side", choices=["BUY", "SELL"], required=True)
    p_wi.add_argument("--qty", type=float, required=True)
    p_wi.add_argument("--limit", type=float, required=True)
    p_wi.add_argument("--exchange", default="SMART")
    p_wi.add_argument("--currency", default="USD")
    _add_common(p_wi)
    p_wi.set_defaults(func=cmd_whatif)

    p_pos = sub.add_parser("positions", help="List positions")
    _add_common(p_pos)
    p_pos.set_defaults(func=cmd_positions)

    p_ops = sub.add_parser("open-orders", help="List open orders")
    _add_common(p_ops)
    p_ops.set_defaults(func=cmd_open_orders)

    p_health = sub.add_parser(
        "health", help="End-to-end health: ping + AAPL delayed quote + what-if"
    )
    _add_common(p_health)
    p_health.set_defaults(func=cmd_health)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
