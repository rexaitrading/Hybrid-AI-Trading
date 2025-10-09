﻿from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.common import *
import os, threading, time

TAGS = "AccountType,NetLiquidation,TotalCashValue,AvailableFunds,BuyingPower,EquityWithLoanValue"

class App(EWrapper, EClient):
    def __init__(self): EClient.__init__(self, self); self.done=False
    def managedAccounts(self, a): print(f"ðŸ‘¤ managedAccounts: {a}", flush=True)
    def nextValidId(self, oid): print(f"âœ… Connected. nextValidId={oid}", flush=True); self.reqAccountSummary(9001,"All",TAGS)
    def accountSummary(self, reqId, account, tag, value, currency): print(f" {account:>10} | {tag:<24} | {value} {currency or ''}", flush=True)
    def accountSummaryEnd(self, reqId): print("â€” accountSummaryEnd â€”", flush=True); self.done=True; self.disconnect()
    def error(self, reqId, code, msg, *_): print(f"âŒ ERROR {code}: {msg}", flush=True)
    def connectionClosed(self): print("ðŸ”Œ connectionClosed", flush=True)

host=os.getenv("IB_HOST","127.0.0.1"); port=int(os.getenv("IB_PORT","4002")); cid=int(os.getenv("IB_CLIENT_ID","101"))
app=App(); print(f"Connecting to {host}:{port} clientId={cid} ...", flush=True); app.connect(host,port,cid)
t=threading.Thread(target=app.run, daemon=True); t.start()

deadline=time.time()+20
while time.time()<deadline and not app.done: time.sleep(0.2)
if not app.done: print("â±ï¸ Timeout waiting for account summary.", flush=True); app.disconnect(); time.sleep(0.3)
print("Done.", flush=True)
