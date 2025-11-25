"""
Unified multi-symbol Phase-5 summary.

Summaries:
- NVDA: logs/nvda_phase5_decisions.json
- SPY : logs/spy_phase5_decisions.json
- QQQ : logs/qqq_phase5_decisions.json

For each symbol:
  day → total, blocked, allowed
"""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

SYMBOLS = {
    "NVDA": Path("logs/nvda_phase5_decisions.json"),
    "SPY":  Path("logs/spy_phase5_decisions.json"),
    "QQQ":  Path("logs/qqq_phase5_decisions.json"),
}

def extract_day(rec):
    # rec["day"], rec["date"], rec["entry_ts"], rec["ts_trade"]
    for key in ("day", "date", "ts_trade", "entry_ts"):
        v = rec.get(key)
        if isinstance(v, str):
            try:
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                return dt.date().isoformat()
            except Exception:
                pass
    return "UNKNOWN"

def load_decisions(path):
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def summarize(symbol, path):
    data = load_decisions(path)
    per_day = defaultdict(lambda: {"total":0,"blocked":0,"allowed":0})
    for rec in data:
        day = extract_day(rec)
        allow = rec.get("allow_flag")
        per_day[day]["total"] += 1
        if allow is False:
            per_day[day]["blocked"] += 1
        else:
            per_day[day]["allowed"] += 1
    return per_day

def main():
    print("[phase5_summary_multi] Phase-5 per-day summary across NVDA/SPY/QQQ:")
    for sym, path in SYMBOLS.items():
        sd = summarize(sym, path)
        print(f"\n=== {sym} ===")
        if not sd:
            print("  (no decisions)")
            continue
        for day in sorted(sd.keys()):
            s = sd[day]
            print(f"  {day}: total={s['total']} blocked={s['blocked']} allowed={s['allowed']}")

if __name__ == "__main__":
    main()