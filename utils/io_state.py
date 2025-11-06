# utils/io_state.py
import datetime as dt
import json
import os
import uuid
from pathlib import Path


def utc_now_str():
    return dt.datetime.utcnow().strftime("%Y-%m-%dT%H%M%SZ")


def ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)


# Ã§â€Â¢Ã§â€Å¸Ã£â‚¬Å’Ã¤Â¸ÂÃ¨Â¦â€ Ã¨â€œâ€¹Ã£â‚¬ÂÃ§Å¡â€žÃ¦â€“Â°Ã¦Âªâ€Ã¥ÂÂÃ¯Â¼Ë†Ã¦â€Â¾Ã¥Å“Â¨ day Ã¥Â­ÂÃ¨Â³â€¡Ã¦â€“â„¢Ã¥Â¤Â¾Ã¥â€¦Â§Ã¯Â¼â€°
def json_path(base_dir: str, day: str, prefix: str):
    ensure_dir(os.path.join(base_dir, day))
    rid = utc_now_str() + "_" + uuid.uuid4().hex[:6]
    return os.path.join(base_dir, day, f"{prefix}_{rid}.json")


# Ã¥Å½Å¸Ã¥Â­ÂÃ¥Â¯Â«Ã¥â€¦Â¥Ã¯Â¼Å¡Ã¥â€¦Ë† .tmp Ã¥â€ ÂÃ¦â€Â¹Ã¥ÂÂÃ¯Â¼Å’Ã©ÂÂ¿Ã¥â€¦ÂÃ¥ÂÅ Ã¦Âªâ€
def atomic_write_json(path: str, obj, indent=2):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)
    os.replace(tmp, path)


# ---- checkpoint (watermark) ----
def _ckpt_dir():
    d = os.path.join(".state")
    ensure_dir(d)
    return d


def load_checkpoint(name: str, default_value: str):
    p = os.path.join(_ckpt_dir(), f"{name}.json")
    if not os.path.exists(p):
        return default_value
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f).get("value", default_value)


def save_checkpoint(name: str, value: str):
    p = os.path.join(_ckpt_dir(), f"{name}.json")
    atomic_write_json(p, {"value": value})
