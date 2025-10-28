# -*- coding: utf-8 -*-
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="RiskHub", version="0.1")

class Decision(BaseModel):
    symbol: str
    qty: float = 0
    notional: float = 0
    side: str = "BUY"

STATE = {
    "kill": False,
    "max_notional": 1_000_000.0
}

@app.get("/health")
def health():
    return {"ok": True, "kill": STATE["kill"], "max_notional": STATE["max_notional"]}

@app.post("/kill")
def set_kill(flag: bool):
    STATE["kill"] = bool(flag)
    return {"ok": True, "kill": STATE["kill"]}

@app.post("/limits")
def set_limits(max_notional: float):
    STATE["max_notional"] = float(max_notional)
    return {"ok": True, "max_notional": STATE["max_notional"]}

@app.post("/decision_check")
def decision_check(d: Decision):
    if STATE["kill"]:
        return {"ok": False, "reason": "kill_switch"}
    if d.notional > STATE["max_notional"]:
        return {"ok": False, "reason": "notional_limit"}
    return {"ok": True, "reason": "pass"}
