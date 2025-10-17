# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os, datetime as dt, pathlib, io, sys

class JsonlLogger:
    def __init__(self, path: str):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: dict):
        rec = dict(record)
        rec.setdefault("ts", dt.datetime.utcnow().isoformat()+"Z")
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def info(self, msg: str, **kw):
        self.write({"level": "INFO", "msg": msg, **kw})

    def error(self, msg: str, **kw):
        self.write({"level": "ERROR", "msg": msg, **kw})