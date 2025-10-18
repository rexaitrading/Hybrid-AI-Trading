# -*- coding: utf-8 -*-
import json, statistics, pathlib
from typing import Tuple

def jsonl_iter(path: str):
    p = pathlib.Path(path)
    if not p.exists(): return
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try: yield json.loads(line)
            except: pass

def decisions_from_log(path: str):
    for rec in jsonl_iter(path):
        if rec.get("msg")=="decision_snapshot" and "result" in rec:
            for d in rec["result"].get("decisions", []):
                yield d

def simple_counts(path: str) -> Tuple[int,int]:
    n_aapl = n_msft = 0
    for d in decisions_from_log(path):
        sym = d.get("symbol")
        if sym=="AAPL": n_aapl += 1
        elif sym=="MSFT": n_msft += 1
    return n_aapl, n_msft