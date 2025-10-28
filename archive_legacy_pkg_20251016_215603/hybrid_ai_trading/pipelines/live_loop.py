# ==== BEGIN CONNECT PATCH (do not remove) ====
import os, sys, time

IB_TIMEOUT = int(os.environ.get('IB_TIMEOUT', '10'))

def _normalize_host(h):
    try:
        return '127.0.0.1' if (h or '').strip().lower() == 'localhost' else h
    except Exception:
        return h

def ib_connect_hardened(ib, host, port, client_id, timeout=None):
    host = _normalize_host(host)
    to = int(os.environ.get('IB_TIMEOUT', str(timeout if timeout is not None else 10)))
    print(f"[loop] connect try host={host} port={port} cid={client_id} timeout={to}")
    ok = ib.connect(host, port, clientId=client_id, timeout=to)
    if ok and ib.isConnected():
        print("[loop] connected on first try"); return True
    try:
        ib.disconnect()
    except Exception:
        pass
    time.sleep(0.5)
    alt = client_id + 1
    print(f"[loop] connect retry host={host} port={port} cid={alt} timeout={to}")
    ok2 = ib.connect(host, port, clientId=alt, timeout=to)
    if ok2 and ib.isConnected():
        print("[loop] connected on retry with cid+1"); return True
    print("[loop] connect failed after two attempts")
    return False
# ==== END CONNECT PATCH ====
import os, time, sys, datetime as dt
import time
import sys
import time
from typing import Dict, Any, List

from ib_insync import IB, util, Stock
import yaml
import time
import sys
import time

from hybrid_ai_trading.common.market import fetch_bars
from hybrid_ai_trading.strategies.equity_momo import momo_signal
from hybrid_ai_trading.execution.route_ib import RiskConfig, place_entry

def load_cfg(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def inside_window(tz_name: str, start_hhmm: str, end_hhmm: str) -> bool:
    try:
        import zoneinfo
import time
import sys
import time
        tz = zoneinfo.ZoneInfo(tz_name)
        now = dt.datetime.now(tz)
    except Exception:
        now = dt.datetime.now()
    hhmm = now.strftime("%H:%M")
    return start_hhmm <= hhmm <= end_hhmm

def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def main() -> int:
    cfg_path = os.environ.get("TRADING_CFG", "hybrid_ai_trading/cfg/paper.yaml")
    cfg = load_cfg(cfg_path)

    ib_host = os.environ.get("IB_HOST", cfg["ib"]["host"])
    ib_port = int(os.environ.get("IB_PORT", cfg["ib"]["port"]))
    client_id = int(os.environ.get("IB_CLIENT_ID", cfg["ib"]["client_id"]))

    tw = cfg["trading_window"]
    tz = tw["tz"]; start = tw["start"]; end = tw["end"]
    # risk / routing settings
    risk_cfg = cfg.get("risk", {})

    # RiskConfig requires positional args:
    #   equity, per_symbol_bp, per_symbol_gross_cap, allow_short, allow_margin
    # We fetch them from config with safe fallbacks.
    _equity      = float(risk_cfg.get("equity", float(os.environ.get("RISK_EQUITY", "100000"))))
    _per_bp      = float(risk_cfg.get("per_symbol_risk_bp", 20.0))
    _per_gross   = float(risk_cfg.get("per_symbol_gross_cap", 15.0))
    _allow_short = bool(cfg["execution"]["allow_short"])
    _allow_margin= bool(cfg["execution"]["allow_margin"])

    rc = RiskConfig(_equity, _per_bp, _per_gross, _allow_short, _allow_margin)

    # Optional knobs: set only if the attr exists on your RiskConfig
    def _set(name, value):
        try:
            if hasattr(rc, name):
                setattr(rc, name, value)
        except Exception:
            pass

    # TIF vs time_in_force
    _tif = str(cfg["execution"]["tif"])
    if hasattr(rc, "tif"):
        rc.tif = _tif
    elif hasattr(rc, "time_in_force"):
        rc.time_in_force = _tif

    # Additional risk caps (best-effort)
    _set("max_gross_leverage", float(risk_cfg.get("max_gross_leverage", 2.0)))
    _set("max_daily_loss_pct", float(risk_cfg.get("max_daily_loss_pct", 1.2)))

    symbols: List[str] = list(cfg["symbols"]["equities"])

    # optional cooldown / pyramid guard via env
    cooldown_sec = int(os.environ.get("COOLDOWN_SEC", "30"))
    allow_pyr = os.environ.get("ALLOW_PYRAMID", "0") == "1"
    last_side: Dict[str, str] = {}
    last_when: Dict[str, float] = {}

    ib = IB()
    print(f"[loop] connecting {ib_host}:{ib_port} cid={client_id}", flush=True)
    # Hardened connect + fail-fast + neutralize any later ib.connect(...)
 ok = ib_connect_hardened(ib, ib_host, ib_port, client_id, timeout=IB_TIMEOUT)
 not ok:
        print("[loop] connect failed (timeout={}s) host={} port={}".format(IB_TIMEOUT, _normalize_host(ib_host), ib_port))
        sys.exit(101)
    # Make any subsequent ib.connect(...) a no-op returning the current IB instance
.connect = (lambda *a, **kw: ib)
    __connect_with_retry(ib, ib_host, ib_port, client_id)
    print(f"[loop] connected: {ib.isConnected()} time: {ib.reqCurrentTime()}", flush=True)

    try:
        while True:
            # heartbeat
            print(f"[hb] {utc_stamp()}", flush=True)

            # trade only inside window
            if not inside_window(tz, start, end):
                time.sleep(15)
                continue

            # scan symbols
            for sym in symbols:
                try:
                    df = fetch_bars(
                        ib, sym,
                        cfg["bars"]["duration"],
                        cfg["bars"]["bar_size"],
                        cfg["bars"]["whatToShow"]
                    )
                    if df is None or df.empty or df.isna().any().any():
                        print(f"[sig] {sym}: FLAT (no data)", flush=True)
                        continue

                    px = float(df["close"].iloc[-1])
                    sig = momo_signal(df, vol_floor_mult=float(risk_cfg.get("vol_floor_atr_mult", 1.0)))

                    # log flat signals lightly
                    if sig.side == "FLAT":
                        print(f"[sig] {sym}: FLAT", flush=True)
                        continue

                    # cooldown / anti-churn guard
                    now_ts = time.time()
                    if not allow_pyr and last_side.get(sym) == sig.side:
                        print(f"[guard] {sym}: same side {sig.side} (pyramid disabled)", flush=True)
                        continue
                    if now_ts - last_when.get(sym, 0.0) < cooldown_sec:
                        print(f"[guard] {sym}: cooldown {cooldown_sec}s", flush=True)
                        continue

                    trade = place_entry(ib, sym, sig.side, px, rc)
                    if trade:
                        last_side[sym] = sig.side
                        last_when[sym] = now_ts
                        print(f"[route] {sym} {sig.side} qty={trade.order.totalQuantity} @~{px}", flush=True)

                except Exception as e:
                    print(f"[warn] {sym}: {e}", flush=True)

                time.sleep(0.4)  # gentle pacing across symbols

            time.sleep(10)  # outer pacing

    finally:
        try:
            ib.disconnect()
        except Exception:
            pass

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
