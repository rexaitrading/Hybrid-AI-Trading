import os
import sys
from pathlib import Path

# pretty output helpers
GREEN = "\x1b[32m"
RED = "\x1b[31m"
YELLOW = "\x1b[33m"
RESET = "\x1b[0m"


def ok(msg):
    print(f"{GREEN}PASS{RESET}  - {msg}")


def warn(msg):
    print(f"{YELLOW}WARN{RESET}  - {msg}")


def err(msg):
    print(f"{RED}FAIL{RESET}  - {msg}")


passed, failed, warned = 0, 0, 0


def _pass(msg):
    global passed
    passed += 1
    ok(msg)


def _fail(msg):
    global failed
    failed += 1
    err(msg)


def _warn(msg):
    global warned
    warned += 1
    warn(msg)


# ---- Step 1: YAML config sanity ----
import yaml

cfg_path = Path("config/config.yaml")
if not cfg_path.exists():
    _fail("config/config.yaml not found")
    sys.exit(1)

try:
    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
except Exception as e:
    _fail(f"config load error: {e}")
    sys.exit(1)

sf = cfg.get("sentiment_filter") or {}
threshold = float(sf.get("threshold", 0.6))
neutral = float(sf.get("neutral_zone", 0.25))
smooth = int(sf.get("smoothing", 3))
if 0.5 <= threshold <= 0.7 and 0.1 <= neutral <= 0.35 and 1 <= smooth <= 5:
    _pass(
        f"YAML: sentiment_filter ok (threshold={threshold}, neutral={neutral}, smoothing={smooth})"
    )
else:
    _fail(
        f"YAML: sentiment_filter unexpected (threshold={threshold}, neutral={neutral}, smoothing={smooth})"
    )

hours_back = int(cfg.get("sweep_hours_back", 6))
limit = int(cfg.get("sweep_limit", 100))
symbols = (cfg.get("sweep_symbols") or "AAPL,MSFT,GOOGL,AMZN,TSLA").upper()
if hours_back > 0 and limit > 0 and "," in symbols:
    _pass(f"YAML: sweep params ok (hours_back={hours_back}, limit={limit}, symbols={symbols})")
else:
    _fail("YAML: sweep params invalid")

rk = cfg.get("risk") or {}
daily_limit = float(rk.get("daily_loss_limit", -0.03))
trade_limit = float(rk.get("trade_loss_limit", -0.005))
if daily_limit <= -0.01 and trade_limit <= -0.002:
    _pass(f"YAML: risk limits ok (daily={daily_limit}, trade={trade_limit})")
else:
    _fail(f"YAML: risk limits unexpected (daily={daily_limit}, trade={trade_limit})")

# ---- Step 2: Sentiment gate check (non-zero stories; at least one ALLOW preferred) ----
try:
    from hybrid_ai_trading.risk.sentiment_gate import score_headlines_for_symbols

    res = score_headlines_for_symbols(symbols, hours_back=hours_back, limit=limit, side="BUY")
    total = int(res.get("total", 0))
    allows = sum(1 for s in res.get("stories", []) if s.get("allow"))
    if total > 0:
        _pass(f"Gate: total stories={total}, allows={allows}")
        if allows == 0:
            _warn("Gate: no ALLOW yet (may be quiet tape or threshold high)")
    else:
        _fail("Gate: zero stories returned (increase sweep_hours_back/limit or check providers)")
except Exception as e:
    _fail(f"Gate error: {e}")

# ---- Step 3: IBKR connectivity & balances (tries LIVE then PAPER) ----
try:
    from ib_insync import IB, Stock

    ib = IB()
    connected = False
    for host, port in [("127.0.0.1", 7496), ("127.0.0.1", 7497)]:
        try:
            ib.connect(host, port, clientId=66)
            connected = True
            which = "LIVE" if port == 7496 else "PAPER"
            _pass(f"IBKR: connected to {which} ({host}:{port})")
            break
        except Exception:
            continue
    if not connected:
        _fail("IBKR: unable to connect (check TWS/Gateway and API settings)")
    else:
        tags = {
            "NetLiquidation": None,
            "AvailableFunds": None,
            "BuyingPower": None,
            "CashBalance": None,
        }
        for item in ib.accountSummary():
            if item.tag in tags:
                tags[item.tag] = item.value
        if all(tags.values()):
            _pass(f"IBKR: balances ok (NLV={tags['NetLiquidation']}, AF={tags['AvailableFunds']})")
        else:
            _fail(f"IBKR: missing balance fields -> {tags}")

        # ---- Step 4: Market data sanity (best-effort) ----
        try:
            contract = Stock("AAPL", "SMART", "USD")
            t = ib.reqMktData(contract, "", False, False)
            ib.sleep(2.0)
            has_px = any(
                [
                    getattr(t, "last", None),
                    getattr(t, "marketPrice", None),
                    (getattr(t, "bid", None) and getattr(t, "ask", None)),
                ]
            )
            if has_px:
                _pass("IBKR: market data tick received for AAPL (bid/ask/last present)")
            else:
                _warn("IBKR: no market tick observed (may lack realtime perms or need longer wait)")
            ib.cancelMktData(contract)
        except Exception as e:
            _warn(f"IBKR: market data check skipped ({e})")
        finally:
            ib.disconnect()
except Exception as e:
    _fail(f"IBKR check error: {e}")

# ---- Step 5: Kill-switch dry-run (no cancel unless explicitly enabled) ----
try:
    kill_ok = False
    # only execute cancel-all if env flag is set
    if os.getenv("KILL_SWITCH_TEST", "").lower() in ("1", "true", "yes"):
        from ib_insync import IB

        ib = IB()
        try:
            ib.connect("127.0.0.1", 7496, clientId=67)
        except Exception:
            ib.connect("127.0.0.1", 7497, clientId=67)
        ords = ib.openTrades()
        if ords:
            ib.reqGlobalCancel()
            _pass(f"Kill-switch: global cancel sent (openTrades={len(ords)})")
            kill_ok = True
        else:
            _pass("Kill-switch: no open orders (nothing to cancel)")
            kill_ok = True
        ib.disconnect()
    else:
        _pass("Kill-switch: dry-run OK (set KILL_SWITCH_TEST=true to exercise cancel)")
        kill_ok = True
    if not kill_ok:
        _fail("Kill-switch: could not verify")
except Exception as e:
    _fail(f"Kill-switch error: {e}")

# ---- Summary ----
print("\n--------- SUMMARY ---------")
print(f"{GREEN}PASS{RESET}: {passed}   {YELLOW}WARN{RESET}: {warned}   {RED}FAIL{RESET}: {failed}")
print("---------------------------")
sys.exit(1 if failed else 0)
