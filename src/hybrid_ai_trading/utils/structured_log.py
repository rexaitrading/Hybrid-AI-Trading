from __future__ import annotations
import json, logging, os, sys, datetime, traceback
from typing import Optional

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # base fields
        payload = {
            "ts": datetime.datetime.utcfromtimestamp(record.created).isoformat(timespec="milliseconds") + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "pid": record.process,
        }
        # source hint
        if record.funcName: payload["func"] = record.funcName
        if record.lineno:   payload["lineno"] = record.lineno
        if record.pathname: payload["file"] = os.path.basename(record.pathname)
        # structured extras (if user passed extra={"kv":...} OR set attributes)
        for k, v in getattr(record, "__dict__", {}).items():
            if k in payload or k.startswith("_"): 
                continue
            # keep only simple JSON-serializable
            try:
                json.dumps(v)
                payload[k] = v
            except Exception:
                payload[k] = str(v)
        # exception info
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)

def setup_logging(level: str="INFO", logfile: Optional[str]=None, json_output: bool=True) -> logging.Logger:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    handler = logging.FileHandler(logfile, encoding="utf-8") if logfile else logging.StreamHandler(sys.stdout)
    fmt = JsonFormatter() if json_output else logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
    handler.setFormatter(fmt)
    root.addHandler(handler)
    return root

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)