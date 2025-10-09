import os, time
import logging, os
if os.getenv("QUIET_LOGS","true").lower() in ("1","true","yes"):
    logging.getLogger().setLevel(logging.ERROR)
    logging.getLogger("hybrid_ai_trading.risk.sentiment_filter").setLevel(logging.ERROR)
print("Scheduler started. Create 'control/PAUSE' to pause, 'control/STOP' to stop with global cancel.")
from datetime import date
import subprocess, sys

CADENCE_S   = int(float(os.getenv("CADENCE_MIN","5"))*60)
MAX_TRADES  = int(os.getenv("MAX_TRADES","5"))

def today_count(logf):
    if not os.path.exists(logf): return 0
    dstr = f"{date.today():%Y%m%d}"
    with open(logf,"r",encoding="utf-8") as f:
        return sum(1 for ln in f if ln.strip() and dstr in ln.split(',')[0])

def once():
    env=os.environ.copy()
    return subprocess.call([sys.executable, "scripts/gate_pick_and_trade_once.py"], env=env)

logf = f"logs/trades_{date.today():%Y%m%d}.csv"
while True:
    if os.path.exists("control/STOP"):
        try:
            from ib_insync import IB
            ib=IB()
            for p in (7496,4001,7497,4002):
                try: ib.connect("127.0.0.1", p, clientId=89, timeout=2); break
                except Exception: pass
            try: ib.reqGlobalCancel(); ib.disconnect()
            except Exception: pass
        except Exception: pass
        print("STOP detected -> exiting."); break

    if os.path.exists("control/PAUSE"):
        time.sleep(CADENCE_S); continue

    if today_count(logf) >= MAX_TRADES:
        time.sleep(CADENCE_S); continue

    once()
    time.sleep(CADENCE_S)