from __future__ import annotations

import os, time, csv, math, json, argparse, datetime as dt
from typing import Dict, Any, List, Iterable, Tuple

# Existing stack
from hybrid_ai_trading.runners.paper_logger import JsonlLogger
from hybrid_ai_trading.runners.paper_config import load_config
import hybrid_ai_trading.runners.paper_quantcore as qc

# RiskHub (optional; log-only)
try:
    from hybrid_ai_trading.utils.risk_client import check_decision, RISK_HUB_URL
except Exception:
    check_decision, RISK_HUB_URL = None, None

"""
Replay Engine (analysis-only):
- Reads historical bars per symbol from CSV (data/<SYM>.csv).
  Expected columns: ts,open,high,low,close,volume
  ts in ISO8601 or '%Y-%m-%d %H:%M:%S' (assumed UTC or market TZ; we treat as naive).

- Plays bars forward at 1× or accelerated (speed>1).
- Each step builds "snapshots" (like live), runs qc.run_once(), logs decision+context.
- Journals to:
  1) JSONL: logs/replay_journal.jsonl (rich context)
  2) CSV:   logs/replay_journal.csv   (flat schema for Notion import)

No routing, no IB calls. Use for "educate & rewire" + pattern mining.
"""

def _parse_ts(s: str) -> dt.datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return dt.datetime.strptime(s, fmt)
        except Exception:
            pass
    # last resort: fromisoformat (py3.11 friendly)
    try:
        return dt.datetime.fromisoformat(s.replace("Z",""))
    except Exception:
        raise ValueError(f"Bad ts format: {s}")

def _read_bars(symbol: str, path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", newline="") as f:
        r = csv.DictReader(f)
        for rec in r:
            rows.append({
                "symbol": symbol,
                "ts": _parse_ts(rec["ts"]),
                "open": float(rec["open"]),
                "high": float(rec["high"]),
                "low": float(rec["low"]),
                "close": float(rec["close"]),
                "volume": float(rec.get("volume", 0) or 0),
            })
    rows.sort(key=lambda x: x["ts"])
    return rows

def _load_universe(cfg: Dict[str, Any], override: str) -> List[str]:
    out: List[str] = []
    base = []
    if isinstance(cfg, dict):
        base = cfg.get("universe") or cfg.get("equities") or []
    if isinstance(base, str):
        base = [x.strip() for x in base.split(",") if x.strip()]
    if isinstance(base, list):
        out.extend([str(x).strip() for x in base if str(x).strip()])
    if override:
        for x in override.split(","):
            x = x.strip()
            if x and x not in out:
                out.append(x)
    return out

def _normalize_result(result):
    if isinstance(result, dict):
        return result
    if isinstance(result, list):
        return {"summary":{"rows":len(result),"batches":1,"decisions":len(result)}, "items": result}
    return {"summary":{"rows":0,"batches":0,"decisions":0}, "items":[]}

def _qc_run_once(symbols, snapshots, cfg, logger):
    fn = getattr(qc, "run_once", None)
    if not callable(fn):
        raise RuntimeError("quantcore.run_once not found")
    # Prefer new signature; fallback if needed
    price_map = {s["symbol"]: s.get("price") for s in snapshots}
    try:
        return _normalize_result(fn(list(symbols), dict(price_map), cfg.get("risk_mgr")))
    except TypeError:
        try:
            return _normalize_result(fn(cfg, logger, snapshots=snapshots))
        except TypeError:
            return _normalize_result(fn(cfg, logger))

def _riskhub_log(snapshots, result, logger):
    if not check_decision:
        logger.info("risk_checks", items=[], note="risk_client_unavailable")
        return
    price_map = {s["symbol"]: float(s.get("price") or 0.0) for s in snapshots}
    items = []
    iterable = (result or {}).get("items") or (result or {}).get("decisions") or []
    for d in iterable:
        if isinstance(d, dict) and "decision" in d:
            sym = d.get("symbol"); dec = d.get("decision") or {}
        else:
            sym = d.get("symbol") if isinstance(d, dict) else None
            dec = d if isinstance(d, dict) else {}
        ks = (dec.get("kelly_size") or {})
        qty = float(ks.get("qty") or dec.get("qty") or 0.0)
        px  = float(price_map.get(sym) or 0.0)
        notion = qty * px
        resp = check_decision(RISK_HUB_URL, sym or "", qty, notion, str(dec.get("side","BUY")))
        items.append({"symbol": sym, "qty": qty, "price": px, "notional": notion, "response": resp})
    logger.info("risk_checks", items=items)

def _snapshot_from_bar(bar: Dict[str, Any]) -> Dict[str, Any]:
    # Mirror live snapshot shape the runner uses
    return {
        "symbol": bar["symbol"],
        "price": float(bar["close"]),
        "bid": None, "ask": None, "last": float(bar["close"]),
        "close": float(bar["close"]), "vwap": None,
        "volume": float(bar["volume"]),
        "ts": bar["ts"].isoformat(),
    }

def _ensure_csv_header(path: str, header: List[str]):
    need = not os.path.exists(path) or os.path.getsize(path) == 0
    if need:
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)

def _append_csv(path: str, row: List[Any]):
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow(row)

def replay_main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/paper_runner.yaml")
    ap.add_argument("--universe", default="")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--speed", type=float, default=5.0, help="1.0 = realtime; 5.0 = 5x faster (sleep scaled down)")
    ap.add_argument("--bars", type=str, default="1m", help="label only")
    ap.add_argument("--log-file", default="logs/replay_journal.jsonl")
    ap.add_argument("--journal-csv", default="logs/replay_journal.csv")
    ap.add_argument("--limit", type=int, default=0, help="max bars to play (0 = all)")
    args = ap.parse_args()

    cfg = {}
    try:
        cfg = load_config(args.config)
    except Exception as e:
        print(f"[replay] config load failed: {e}")

    symbols = _load_universe(cfg, args.universe)
    if not symbols:
        print("[replay] empty universe; nothing to do.")
        return 0

    os.makedirs(os.path.dirname(args.log_file) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(args.journal_csv) or ".", exist_ok=True)
    logger = JsonlLogger(args.log_file)

    # Journal CSV (flat) -> Notion import
    header = [
        "ts","symbol","price","setup","side","qty",
        "kelly_f","confidence","reason",
        "regime","sentiment","notes"
    ]
    _ensure_csv_header(args.journal_csv, header)

    # Load bars per symbol
    bars: Dict[str,List[Dict[str,Any]]] = {}
    for sym in symbols:
        pth = os.path.join(args.data_dir, f"{sym}.csv")
        if not os.path.exists(pth):
            raise FileNotFoundError(f"Missing bars file: {pth}")
        bars[sym] = _read_bars(sym, pth)

    # Build a merged time cursor across symbols (zip bars by index)
    # Simple strategy: iterate by index until any symbol runs out.
    total = min(len(b) for b in bars.values())
    if args.limit and args.limit > 0:
        total = min(total, args.limit)

    logger.info("replay_start", config={"speed": args.speed, "bars": args.bars}, symbols=symbols, total_steps=total)

    # Play forward
    for i in range(total):
        step_bars = {sym: bars[sym][i] for sym in symbols}
        snapshots = [_snapshot_from_bar(step_bars[s]) for s in symbols]

        # Run QC once (analysis-only)
        try:
            result = _qc_run_once(symbols, snapshots, cfg, logger)
        except Exception as e:
            logger.error("qc_error", error=str(e))
            result = {"summary":{"rows":0,"batches":0,"decisions":0}, "items":[]}

        # RiskHub log-only
        try:
            _riskhub_log(snapshots, result, logger)
        except Exception as e:
            logger.info("risk_checks", items=[], note=f"risk_log_error:{e}")

        # Journal decisions -> CSV
        items = (result or {}).get("items") or []
        for d in items:
            if isinstance(d, dict) and "decision" in d:
                sym = d.get("symbol"); dec = d.get("decision") or {}
            else:
                sym = d.get("symbol") if isinstance(d, dict) else None
                dec = d if isinstance(d, dict) else {}
            ks = dec.get("kelly_size") or {}
            row = [
                step_bars[sym]["ts"].isoformat() if sym in step_bars else snapshots[0]["ts"],
                sym,
                float(step_bars[sym]["close"]) if sym in step_bars else float(snapshots[0]["price"] or 0.0),
                dec.get("setup",""),                         # optional: your QC can set this
                (dec.get("side") or "BUY"),
                int(ks.get("qty") or dec.get("qty") or 0),
                float(ks.get("f") or 0.0),
                float(dec.get("confidence") or 0.0),
                str(dec.get("reason") or ""),
                str(((dec.get("regime") or {}).get("regime", "")) if isinstance(dec.get("regime"), dict) else ""),
                str(((dec.get("sentiment") or {}).get("sentiment", "")) if isinstance(dec.get("sentiment"), dict) else ""),
                ""  # notes placeholder; can fill later
            ]
            _append_csv(args.journal_csv, row)

        # JSONL checkpoint for step
        logger.info("replay_step", idx=i, snapshots=snapshots, result=result)

        # Timing: simple 1-second bar emulation scaled by speed
        sleep_s = 1.0 / max(1.0, float(args.speed))
        time.sleep(sleep_s)

    logger.info("replay_done", total_steps=total)
    return 0

if __name__ == "__main__":
    raise SystemExit(replay_main())
