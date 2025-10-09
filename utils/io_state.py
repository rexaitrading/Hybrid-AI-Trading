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


# ç”¢ç”Ÿã€Œä¸è¦†è“‹ã€çš„æ–°æª”åï¼ˆæ”¾åœ¨ day å­è³‡æ–™å¤¾å…§ï¼‰
def json_path(base_dir: str, day: str, prefix: str):
    ensure_dir(os.path.join(base_dir, day))
    rid = utc_now_str() + "_" + uuid.uuid4().hex[:6]
    return os.path.join(base_dir, day, f"{prefix}_{rid}.json")


# åŽŸå­å¯«å…¥ï¼šå…ˆ .tmp å†æ”¹åï¼Œé¿å…åŠæª”
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
