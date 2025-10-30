import os
import signal
import sys
import time
from collections import deque
from datetime import timedelta

import pandas as pd
from ib_insync import *

from hybrid_ai_trading.tools.bar_replay import run_replay

# ---- Env / config ----
HOST = os.getenv("IB_HOST", "127.0.0.1")
PORT = int(os.getenv("IB_PORT", "4002"))
CID = int(os.getenv("IB_CLIENT_ID", "7"))

SYMBOL = os.getenv("LIVE_SYMBOL", "AAPL")
PRIMARY = os.getenv("LIVE_PRIMARY", "NASDAQ")
ORB_MIN = int(os.getenv("LIVE_ORB_MINUTES", "15"))
QTY = int(os.getenv("LIVE_QTY", "100"))
FEES = float(os.getenv("LIVE_FEES", "0"))
MODE = os.getenv("LIVE_MODE", "auto")
USE_RTH = os.getenv("LIVE_USE_RTH", "1") in ("1", "true", "True", "YES", "yes")
MDT = int(os.getenv("LIVE_MDT", "3"))  # 1=live,2=freeze,3=delayed,4=delayed-frozen

SEED_MIN = max(ORB_MIN + 10, 45)
DUR_SEC = SEED_MIN * 60

ib = IB()


# ---- Helpers ----
def _call_run_replay(*, df, symbol, mode, qty, fees, orb_minutes, force_exit, notion):
    # Call run_replay with only the kwargs it supports (version-agnostic)
    try:
        import inspect

        sig = inspect.signature(run_replay)
        params = set(sig.parameters.keys())

        base = {
            "df": df,
            "symbol": symbol,
            "mode": mode,
            "orb_minutes": orb_minutes,
            "force_exit": force_exit,
            "notion": notion,
        }
        for k in ("qty", "quantity", "size", "units", "order_qty"):
            if k in params:
                base[k] = qty
                break
        for k in ("fees", "fee", "commission", "commissions"):
            if k in params:
                base[k] = fees
                break
        if "speed" in params:
            base["speed"] = 5.0

        call_kwargs = {k: v for k, v in base.items() if k in params}
        return run_replay(**call_kwargs)
    except Exception as e:
        print(f"[compat] run_replay signature adaptation failed: {e!r}", flush=True)
        try:
            return run_replay(
                df=df,
                symbol=symbol,
                mode=mode,
                orb_minutes=orb_minutes,
                force_exit=force_exit,
                notion=notion,
            )
        except Exception as e2:
            print(f"[fatal] run_replay fallback failed: {e2!r}", flush=True)
            raise


def _extract_summary(res):
    try:
        if res is None:
            return {"result": None}
        if isinstance(res, dict):
            return res.get("summary", res)
        if hasattr(res, "summary"):
            s = getattr(res, "summary")
            try:
                return dict(s)
            except Exception:
                return s
        if hasattr(res, "to_dict"):
            try:
                return res.to_dict()
            except Exception:
                pass
        if hasattr(res, "_asdict"):
            try:
                return res._asdict()
            except Exception:
                pass
        if isinstance(res, tuple):
            try:
                return list(res)
            except Exception:
                pass
        return {"result": str(res)}
    except Exception as e:
        return {"result": repr(res), "note": f"extract_fail: {e!r}"}


def qualify(symbol, primary):
    c = (
        Stock(symbol, "SMART", "USD", primaryExchange=primary)
        if primary
        else Stock(symbol, "SMART", "USD")
    )
    cs = ib.qualifyContracts(c)
    if not cs:
        raise RuntimeError(f"Contract qualify failed for {symbol}")
    return cs[0]


def seed_history(contract):
    attempts = [
        dict(
            durationStr=f"{DUR_SEC} S",
            barSizeSetting="1 min",
            whatToShow="TRADES",
            useRTH=USE_RTH,
        ),
        dict(
            durationStr=f"{DUR_SEC} S",
            barSizeSetting="1 min",
            whatToShow="TRADES",
            useRTH=False,
        ),
        dict(
            durationStr="1 D",
            barSizeSetting="1 min",
            whatToShow="TRADES",
            useRTH=USE_RTH,
        ),
    ]
    for i, kw in enumerate(attempts, 1):
        try:
            print(f"[seed] attempt {i}: {kw}", flush=True)
            bars = ib.reqHistoricalData(
                contract, endDateTime="", formatDate=1, keepUpToDate=False, **kw
            )
            if bars:
                df = pd.DataFrame(
                    [
                        {
                            "timestamp": (
                                b.date
                                if isinstance(b.date, str)
                                else b.date.strftime("%Y-%m-%d %H:%M:%S")
                            ),
                            "open": b.open,
                            "high": b.high,
                            "low": b.low,
                            "close": b.close,
                            "volume": b.volume,
                        }
                        for b in bars
                    ]
                )
                print(f"[seed] received {len(df)} bars.", flush=True)
                return df
            else:
                print("[seed] 0 bars", flush=True)
        except Exception as e:
            print(f"[seed] error: {e!r}", flush=True)
            time.sleep(1.0)
    print("[seed] all attempts failed; proceeding with stream only.", flush=True)
    return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])


class _RT:
    __slots__ = ("time", "open", "high", "low", "close", "volume", "wap", "count")

    def __init__(self, t, o, h, l, c, v, w=0.0, count=1):
        self.time = t
        self.open = o
        self.high = h
        self.low = l
        self.close = c
        self.volume = v
        self.wap = w
        self.count = count


def to_row(b):
    return {
        "timestamp": getattr(b, "time", None) or getattr(b, "date", None),
        "open": float(b.open),
        "high": float(b.high),
        "low": float(b.low),
        "close": float(b.close),
        "volume": int(getattr(b, "volume", 0) or 0),
    }


def resample_5s_to_1m(df):
    if df.empty:
        return df
    x = df.set_index(pd.to_datetime(df["timestamp"])).sort_index()
    ohlc = (
        x[["open", "high", "low", "close"]]
        .resample("1min", label="right", closed="right")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
    )
    vol = x[["volume"]].resample("1min", label="right", closed="right").sum()
    out = pd.concat([ohlc, vol], axis=1).dropna().reset_index()
    out.rename(columns={"index": "timestamp"}, inplace=True)
    out["timestamp"] = out["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    return out


def _simulate_from_seed(seed_df, *, state, pace_sec=0.10):
    # Drive per-minute synthetic ticks from seed when markets are closed
    if seed_df.empty:
        print("[sim] no seed to simulate from", flush=True)
        return
    # Start strictly after the last seed minute
    t0_ts = pd.to_datetime(seed_df["timestamp"].iloc[-1])
    t0 = t0_ts.to_pydatetime() if hasattr(t0_ts, "to_pydatetime") else t0_ts
    tail = seed_df.reset_index(drop=True)
    n = len(tail)
    print(f"[sim] driving {n} minute bars from seed (starting after {t0})", flush=True)
    for i in range(1, n + 1):
        r = tail.iloc[i - 1]
        # pure datetime math -> no .to_pydatetime() needed
        t = (t0 + timedelta(minutes=i)).replace(second=0, microsecond=0)
        b = _RT(
            t,
            r["open"],
            r["high"],
            r["low"],
            r["close"],
            int(r["volume"]),
            w=r["close"],
            count=1,
        )
        on_rt_bar(b, state=state)
        time.sleep(pace_sec)
    print("[sim] complete", flush=True)


def on_rt_bar(rtbar, *, state):
    state["five_s"].append(rtbar)
    if rtbar.time.second % 60 != 0:
        return
    df_5s = pd.DataFrame([to_row(b) for b in state["five_s"]])
    df_1m = resample_5s_to_1m(df_5s)
    if df_1m.empty:
        return
    ts_last = df_1m["timestamp"].iloc[-1]
    # drop duplicates at the same timestamp
    if state.get("last_ts") == ts_last:
        return
    state["last_ts"] = ts_last
    print(f"[tick] 1m close: {ts_last}  rows={len(df_1m)}", flush=True)
    tail = df_1m.tail(ORB_MIN + 5)
    if len(tail) >= ORB_MIN + 5:
        # pass a copy to avoid pandas SettingWithCopyWarning in downstream code
        res = _call_run_replay(
            df=tail.copy(),
            symbol=SYMBOL,
            mode=MODE,
            qty=QTY,
            fees=FEES,
            orb_minutes=ORB_MIN,
            force_exit=True,
            notion=False,
        )
        summary = _extract_summary(res)
        print(f"[live] {ts_last} {summary}", flush=True)


def run_from_csv(csv_path):
    # Load minute bars from CSV and drive SIM without IB
    import os

    df = pd.read_csv(csv_path)
    cols = {c.lower(): c for c in df.columns}
    required = ["timestamp", "open", "high", "low", "close"]
    for k in required:
        if k not in cols:
            raise ValueError(f"CSV missing required column: {k}")
    # Normalize column names
    df = df.rename(
        columns={
            cols["timestamp"]: "timestamp",
            cols["open"]: "open",
            cols["high"]: "high",
            cols["low"]: "low",
            cols["close"]: "close",
        }
    )
    if "volume" in cols:
        df = df.rename(columns={cols["volume"]: "volume"})
    else:
        df["volume"] = 0
    # Ensure string timestamps for our existing pipeline
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    # Build seed + state, then drive SIM
    print(f"[csv] loaded {len(df)} rows from {csv_path}", flush=True)
    five_s = deque(maxlen=12000)
    for _, r in df.tail(SEED_MIN).iterrows():
        t = pd.to_datetime(r["timestamp"]).to_pydatetime()
        five_s.append(
            _RT(
                t,
                r["open"],
                r["high"],
                r["low"],
                r["close"],
                int(r["volume"]),
                w=r["close"],
                count=1,
            )
        )
    state = {"five_s": five_s}
    if os.getenv("LIVE_SIM", "0") not in ("1", "true", "True", "YES", "yes"):
        os.environ["LIVE_SIM"] = "1"
    _simulate_from_seed(df.tail(ORB_MIN + 8), state=state, pace_sec=0.05)


def main():
    print(f"[connect] {HOST}:{PORT} cid={CID} symbol={SYMBOL}", flush=True)
    ib.connect(HOST, PORT, clientId=CID)

    ib.reqMarketDataType(MDT)
    print(f"[mdt] using type {MDT}", flush=True)

    contract = qualify(SYMBOL, PRIMARY)
    print(f"[qualified] {contract}", flush=True)

    seed_df = seed_history(contract)

    print("[stream] subscribing 5s TRADES bars ...", flush=True)
    five_s = deque(maxlen=12000)
    for _, r in seed_df.iterrows():
        t = pd.to_datetime(r["timestamp"]).to_pydatetime()
        five_s.append(
            _RT(
                t,
                r["open"],
                r["high"],
                r["low"],
                r["close"],
                int(r["volume"]),
                w=r["close"],
                count=1,
            )
        )

    # SIM mode path
    if os.getenv("LIVE_SIM", "0") in ("1", "true", "True", "YES", "yes"):
        state = {"five_s": five_s}
        print(
            "[sim] LIVE_SIM=1 -> using synthetic minute ticks from seed (no RT subscription)",
            flush=True,
        )
        _simulate_from_seed(seed_df.tail(ORB_MIN + 8), state=state, pace_sec=0.10)
        return

    # RT subscription (strong ref)
    bars = ib.reqRealTimeBars(contract, 5, "TRADES", USE_RTH, [])
    state = {"five_s": five_s, "bars": bars}

    def _on_update(bars_list, hasNewBar):
        if not hasNewBar:
            return
        rtbar = bars_list[-1]
        on_rt_bar(rtbar, state=state)

    bars.updateEvent += _on_update

    def stop(*_):
        print("[shutdown] disconnecting...", flush=True)
        try:
            ib.disconnect()
        finally:
            sys.exit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    print(
        f"[ready] seed={len(seed_df)}  orb_min={ORB_MIN}  qty={QTY}  fees={FEES}  mode={MODE}  useRTH={USE_RTH}",
        flush=True,
    )
    ib.run()


if __name__ == "__main__":
    import argparse
    import os

    p = argparse.ArgumentParser(
        description="Live ORB play-forward runner (with optional SIM & CSV)"
    )
    p.add_argument(
        "--sim", action="store_true", help="Enable SIM mode (no RT subscription)"
    )
    p.add_argument(
        "--from-csv",
        type=str,
        default=None,
        help="Path to minute-bar CSV to drive SIM without IB",
    )
    p.add_argument("--symbol", type=str, default=os.getenv("LIVE_SYMBOL", "AAPL"))
    p.add_argument("--primary", type=str, default=os.getenv("LIVE_PRIMARY", "NASDAQ"))
    p.add_argument(
        "--mdt", type=int, choices=[1, 2, 3, 4], default=int(os.getenv("LIVE_MDT", "3"))
    )
    p.add_argument(
        "--rth",
        type=int,
        choices=[0, 1],
        default=(
            1
            if os.getenv("LIVE_USE_RTH", "1") in ("1", "true", "True", "YES", "yes")
            else 0
        ),
    )
    p.add_argument("--qty", type=int, default=int(os.getenv("LIVE_QTY", "100")))
    p.add_argument("--fees", type=float, default=float(os.getenv("LIVE_FEES", "0")))
    p.add_argument(
        "--orb-minutes", type=int, default=int(os.getenv("LIVE_ORB_MINUTES", "15"))
    )
    args = p.parse_args()

    # push into env so existing code paths keep working
    os.environ["LIVE_SYMBOL"] = args.symbol
    os.environ["LIVE_PRIMARY"] = args.primary
    os.environ["LIVE_MDT"] = str(args.mdt)
    os.environ["LIVE_USE_RTH"] = "1" if args.rth == 1 else "0"
    os.environ["LIVE_QTY"] = str(args.qty)
    os.environ["LIVE_FEES"] = str(args.fees)
    os.environ["LIVE_ORB_MINUTES"] = str(args.orb_minutes)
    if args.sim:
        os.environ["LIVE_SIM"] = "1"

    try:
        if args.from_csv:
            run_from_csv(args.from_csv)
        else:
            main()
    except Exception as e:
        print("[fatal]", repr(e), file=sys.stderr)
        try:
            ib.disconnect()
        except Exception:
            pass
        sys.exit(1)
