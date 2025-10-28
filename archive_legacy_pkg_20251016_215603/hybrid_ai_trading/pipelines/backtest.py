#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Backtest pipeline (TWS Paper) – robust, self-contained

- Auto-detects IB_HOST (if not provided) via API handshake on ::1/localhost/127.0.0.1
- Connects with ib_insync to TWS Paper (default port 7497) using IB_CLIENT_ID
- Downloads historical bars and runs a tiny SMA crossover backtest
- Writes results CSV into ./outputs/
- Exit codes:
    0  success
    10 no listener / handshake failed
    11 ib_insync not installed / import failure
    12 connection failed
    13 historical data failure
    14 no bars returned
    15 unexpected exception
"""

import argparse
import csv
import datetime as dt
import os
import socket
import sys
from typing import List, Optional, Tuple

try:
    from ib_insync import IB, Stock, util
except Exception as e:
    sys.stderr.write(f"[ERR] ib_insync import failed: {e}\n")
    sys.exit(11)


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def api_handshake(host: str, port: int, timeout_ms: int = 2000) -> int:
    """Return bytes read after sending 'API\\0' or -1 on error."""
    try:
        infos = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        last_err = None
        for family, socktype, proto, canonname, sockaddr in infos:
            try:
                s = socket.socket(family, socktype, proto)
                s.settimeout(timeout_ms / 1000.0)
                s.connect(sockaddr)
                s.sendall(b"API\x00")
                data = s.recv(64)
                s.close()
                return len(data)
            except Exception as err:
                last_err = err
                continue
        return -1 if last_err else 0
    except Exception:
        return -1


def choose_host(port: int, timeout_ms: int = 2000) -> Optional[str]:
    """Pick a host that responds to the API handshake."""
    for host in ("::1", "localhost", "127.0.0.1"):
        n = api_handshake(host, port, timeout_ms)
        print(f"[handshake] {host}:{port} -> {n} bytes")
        if n > 0:
            return host
    return None


def sma(series: List[float], period: int) -> List[Optional[float]]:
    out = [None] * len(series)
    if period <= 0:
        return out
    acc = 0.0
    q: List[float] = []
    for i, v in enumerate(series):
        q.append(v)
        acc += v
        if len(q) > period:
            acc -= q.pop(0)
        if len(q) == period:
            out[i] = acc / period
    return out


def backtest_sma_close(bars: List[Tuple[dt.datetime, float]], fast: int, slow: int):
    """Return (pnl_pct, trades). bars: (datetime, close)."""
    closes = [c for _, c in bars]
    fast_sma = sma(closes, fast)
    slow_sma = sma(closes, slow)
    pos = 0
    entry_price = 0.0
    trades = []
    pnl = 0.0

    for i in range(len(bars)):
        if fast_sma[i] is None or slow_sma[i] is None:
            continue
        t, px = bars[i]
        if pos == 0:
            if (
                fast_sma[i] > slow_sma[i]
                and fast_sma[i - 1] is not None
                and slow_sma[i - 1] is not None
                and fast_sma[i - 1] <= slow_sma[i - 1]
            ):
                pos = 1
                entry_price = px
                trades.append((t, "BUY", px))
        else:
            if (
                fast_sma[i] < slow_sma[i]
                and fast_sma[i - 1] is not None
                and slow_sma[i - 1] is not None
                and fast_sma[i - 1] >= slow_sma[i - 1]
            ):
                pos = 0
                pnl += (px - entry_price) / entry_price
                trades.append((t, "SELL", px))

    if pos == 1 and bars:
        last_px = bars[-1][1]
        pnl += (last_px - entry_price) / entry_price
        trades.append((bars[-1][0], "SELL_EOD", last_px))

    return pnl * 100.0, trades


def main() -> int:
    parser = argparse.ArgumentParser(description="Hybrid AI Trading - Backtest (TWS Paper)")
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--exchange", default="SMART")
    parser.add_argument("--currency", default="USD")
    parser.add_argument("--duration", default="2 D")
    parser.add_argument("--barSize", default="5 mins")
    parser.add_argument("--whatToShow", default="TRADES")
    parser.add_argument("--useDelayed", action="store_true")
    parser.add_argument("--fast", type=int, default=10)
    parser.add_argument("--slow", type=int, default=20)
    parser.add_argument("--outfile", default=None)
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()

    port_env = os.getenv("IB_PORT", "").strip()
    host_env = os.getenv("IB_HOST", "").strip()
    client_env = os.getenv("IB_CLIENT_ID", "").strip()

    port = int(port_env) if port_env.isdigit() else 7497
    client_id = int(client_env) if client_env.isdigit() else 3021

    if host_env:
        host = host_env
        print(f"[cfg] Using IB_HOST from env: {host}:{port}")
    else:
        print("[cfg] IB_HOST not set; probing ::1/localhost/127.0.0.1 via API handshake...")
        host = choose_host(port, timeout_ms=2000)
        if not host:
            sys.stderr.write("[ERR] Could not arm API handshake on ::1/localhost/127.0.0.1\n")
            return 10
        print(f"[cfg] Chosen host via handshake: {host}:{port}")

    ib = IB()
    try:
        print(
            f"[ib] Connecting to {host}:{port} (clientId={client_id}, timeout={args.timeout}) ..."
        )
        ok = ib.connect(host, port, clientId=client_id, timeout=args.timeout)
        if not ok or not ib.isConnected():
            sys.stderr.write("[ERR] ib.connect returned False / not connected\n")
            return 12
        print(f"[ib] Connected: {ib.isConnected()}  Time: {ib.reqCurrentTime()}")
    except Exception as e:
        sys.stderr.write(f"[ERR] IB connection failed: {e}\n")
        return 12

    try:
        ib.reqMarketDataType(3 if args.useDelayed else 1)
    except Exception as e:
        sys.stderr.write(f"[WARN] reqMarketDataType failed: {e}\n")

    contract = Stock(args.symbol, args.exchange, args.currency)
    print(
        f"[ib] Requesting historical data: {args.symbol} {args.duration} {args.barSize} {args.whatToShow}"
    )
    try:
        bars = ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr=args.duration,
            barSizeSetting=args.barSize,
            whatToShow=args.whatToShow,
            useRTH=False,
            formatDate=1,
            keepUpToDate=False,
        )
    except Exception as e:
        sys.stderr.write(f"[ERR] reqHistoricalData failed: {e}\n")
        ib.disconnect()
        return 13

    if not bars:
        sys.stderr.write(
            "[ERR] No bars returned (check permissions / symbol / whatToShow / duration)\n"
        )
        ib.disconnect()
        return 14

    series = []
    for b in bars:
        series.append(
            (
                b.date if isinstance(b.date, dt.datetime) else util.parseIBDatetime(b.date),
                float(b.close),
            )
        )

    pnl_pct, trades = backtest_sma_close(series, args.fast, args.slow)

    ensure_dir("./outputs")
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    outpath = args.outfile or os.path.join("outputs", f"backtest_{args.symbol}_{ts}.csv")
    with open(outpath, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "price"])
        for t, px in series:
            w.writerow([t.isoformat(), f"{px:.6f}"])
        w.writerow([])
        w.writerow(["trades"])
        w.writerow(["time", "side", "price"])
        for t, side, px in trades:
            w.writerow([t.isoformat(), side, f"{px:.6f}"])
        w.writerow([])
        w.writerow(["summary"])
        w.writerow(["symbol", "fast", "slow", "pnl_pct"])
        w.writerow([args.symbol, args.fast, args.slow, f"{pnl_pct:.4f}"])

    print(f"[done] Results -> {outpath}")
    print(f"[done] PnL: {pnl_pct:.4f}%  Trades: {len(trades)}")
    try:
        ib.disconnect()
    finally:
        pass
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except KeyboardInterrupt:
        sys.stderr.write("[INTERRUPTED]\n")
        rc = 15
    except Exception as e:
        sys.stderr.write(f"[ERR] Unexpected: {e}\n")
        rc = 15
    sys.exit(rc)


from hybrid_ai_trading.common.market import fetch_bars
