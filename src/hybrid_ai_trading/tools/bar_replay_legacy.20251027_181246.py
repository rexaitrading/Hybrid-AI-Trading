#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, sys, time, json, math, argparse, textwrap
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, Iterator
import pandas as pd
import numpy as np
try:
    import requests
except Exception:
    requests = None

def _http_get(url: str) -> bytes:
    if requests is not None:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.content
    import urllib.request
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.read()
try:
    import requests
try:
    import requests
except Exception:
    requests = None

def _http_get(url: str) -> bytes:
    if requests is not None:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.content
    import urllib.request
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.read()
except Exception:
    requests = None

def _http_get(url: str) -> bytes:
    if requests is not None:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.content
    import urllib.request
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.read()
NOTION_VERSION = "2022-06-28"

def _to_datetime_col(s: pd.Series) -> pd.Series:
    try:
        if np.issubdtype(s.dtype, np.number):
            mx = float(np.nanmax(s.values))
            if mx > 1e12 or mx > 1e10:
                return pd.to_datetime(s, unit="ms", utc=True)
            return pd.to_datetime(s, unit="s", utc=True)
        return pd.to_datetime(s, utc=True)
    except Exception:
        return pd.to_datetime(s, utc=True, errors="coerce")

def _sleep_secs(seconds: float):
    if seconds <= 0: return
    t0 = time.time()
    while True:
        left = seconds - (time.time() - t0)
        if left <= 0: break
        time.sleep(min(left, 0.05))

class NotionClient:
    def __init__(self, token: str, version: str = NOTION_VERSION):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Notion-Version": version,
            "Content-Type": "application/json",
        })
    def users_me(self) -> Dict[str, Any]:
        r = self.session.get("https://api.notion.com/v1/users/me", timeout=15); r.raise_for_status(); return r.json()
    def databases_get(self, db_id: str) -> Dict[str, Any]:
        r = self.session.get(f"https://api.notion.com/v1/databases/{db_id}", timeout=20); r.raise_for_status(); return r.json()
    def pages_create(self, parent_database_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"parent": {"database_id": parent_database_id}, "properties": properties}
        r = self.session.post("https://api.notion.com/v1/pages", data=json.dumps(payload), timeout=30); r.raise_for_status(); return r.json()

@dataclass
class JournalSchema:
    title_name: str
    types: Dict[str, str]

def fetch_schema(notion: NotionClient, db_id: str) -> JournalSchema:
    meta = notion.databases_get(db_id)
    props = meta.get("properties", {})
    title_name = None
    types = {}
    for k, v in props.items():
        t = v.get("type"); types[k] = t
        if t == "title" and title_name is None: title_name = k
    if not title_name: raise RuntimeError("No title property found in Notion DB.")
    return JournalSchema(title_name=title_name, types=types)

def notion_richtext(text: str) -> Dict[str, Any]:
    return {"rich_text": [{"type": "text", "text": {"content": text[:2000]}}]}
def notion_title(text: str) -> Dict[str, Any]:
    return {"title": [{"type": "text", "text": {"content": text[:2000]}}]}

def build_replay_properties(schema: JournalSchema, name: str, symbol: str,
                            qty: Optional[int], entry_px: Optional[float], exit_px: Optional[float],
                            fees: Optional[float], kelly_f: Optional[float], notes: str,
                            extras: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    p: Dict[str, Any] = {}
    p[schema.title_name] = notion_title(name)
    def has(k, t=None):
        if k not in schema.types: return False
        return (t is None) or (schema.types[k] == t)
    if has("symbol","rich_text"):     p["symbol"]    = notion_richtext(symbol)
    if has("qty","number") and qty is not None:           p["qty"]      = {"number": int(qty)}
    if has("entry_px","number") and entry_px is not None: p["entry_px"] = {"number": float(entry_px)}
    if has("exit_px","number") and exit_px is not None:   p["exit_px"]  = {"number": float(exit_px)}
    if has("fees","number") and fees is not None:         p["fees"]     = {"number": float(fees)}
    if has("kelly_f","number") and kelly_f is not None:   p["kelly_f"]  = {"number": float(kelly_f)}
    if has("Notes","rich_text"):      p["Notes"]     = notion_richtext(notes)
    elif has("notes","rich_text"):    p["notes"]     = notion_richtext(notes)
    if has("side","select"):
        side_val = None
        if entry_px is not None and exit_px is None: side_val = "BUY"
        elif entry_px is not None and exit_px is not None: side_val = ("SELL" if exit_px < entry_px else "BUY")
        if side_val: p["side"] = {"select": {"name": side_val}}
    if extras: p.update(extras)
    return p

@dataclass
class Position:
    side: Optional[str] = None
    entry_px: Optional[float] = None
    qty: int = 0

@dataclass
class ReplayResult:
    bars: int
    trades: int
    pnl: float
    entry_px: Optional[float]
    exit_px: Optional[float]
    final_pos: Position

def orb_strategy_step(idx: int, row: pd.Series, pos: Position,
                      orb_high: float, orb_low: float,
                      risk_cents: float, max_qty: int) -> Tuple[Position, Optional[str]]:
    """
    Enter long on break above ORB high. Signal exit when close < ORB low.
    Do NOT flatten here; just signal with action string.
    """
    act = None
    close = float(row["close"])
    if pos.side is None:
        if close > orb_high:
            denom = max(0.01, (close - orb_low))
            qty = max(1, min(max_qty, int(max(1, math.floor((risk_cents/100.0)/denom)))))
            pos = Position(side="long", entry_px=close, qty=qty)
            act = f"enter_long qty={qty} px={close:.2f}"
    else:
        if close < orb_low:
            act = f"exit_long qty={pos.qty} px={close:.2f}"
    return pos, act

def run_replay(df: pd.DataFrame, symbol: str, mode: str = "step", speed: float = 5.0,
               fees_per_share: float = 0.003, orb_minutes: int = 5,
               risk_cents: float = 20.0, max_qty: int = 200,
               force_exit: bool = False) -> ReplayResult:
    assert mode in ("step","auto")
    if "timestamp" in df.columns:
        df["timestamp"] = _to_datetime_col(df["timestamp"])
        df = df.set_index("timestamp")
    df = df.sort_index()
    needed = {"open","high","low","close","volume"}
    if not needed.issubset(df.columns): raise ValueError("Data must have columns: open, high, low, close, volume (+ timestamp or dt index)")
    if len(df) < (orb_minutes + 5): raise ValueError(f"Not enough bars for ORB ({len(df)} given)")

    orb_df = df.iloc[:orb_minutes]
    orb_high = float(orb_df["high"].max()); orb_low = float(orb_df["low"].min())

    pos = Position(); trades = 0; entry_px = None; exit_px = None; pnl = 0.0
    for i, (ts, row) in enumerate(df.iloc[orb_minutes:].iterrows(), start=orb_minutes):
        prev_qty = pos.qty  # capture size BEFORE exit
        pos, action = orb_strategy_step(i, row, pos, orb_high, orb_low, risk_cents, max_qty)
        close_px = float(row["close"])

        if action and action.startswith("enter_long"):
            trades += 1
            entry_px = close_px
            # pos.qty set by strategy
        elif action and action.startswith("exit_long"):
            trades += 1
            exit_px = close_px
            if entry_px is not None:
                q = prev_qty if prev_qty and prev_qty > 0 else (pos.qty if pos.qty else 1)
                pnl += (exit_px - entry_px) * q
                pnl -= (fees_per_share * q) * 2
            # flatten AFTER PnL
            pos = Position()
            entry_px = None

        try:
            if mode == "step":
                input(f"[{ts}] {symbol} close={row['close']:.2f}  (Enter=next, Ctrl+C to stop)")
            else:
                _sleep_secs(1.0 / max(0.1, speed))
        except KeyboardInterrupt:
            print(f"[replay] aborted by user at {ts}")
            break

    # if still in position on the last bar
    last_close = float(df.iloc[-1]["close"])
    if pos.side == "long" and entry_px is not None:
        q = pos.qty if pos.qty else max_qty
        if force_exit:
            exit_px = last_close
            pnl += (exit_px - entry_px) * q
            pnl -= (fees_per_share * q)
            pos = Position()
        else:
            pnl += (last_close - entry_px) * q
            pnl -= (fees_per_share * q)

    return ReplayResult(
        bars=len(df), trades=trades, pnl=float(round(pnl,2)),
        entry_px=entry_px, exit_px=exit_px, final_pos=pos
    )

def load_bars(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext in [".parquet",".pq",".pqt"]: df = pd.read_parquet(path)
    else: df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    return df

def main():
    ap = argparse.ArgumentParser(description="Bar Replay Engine with Notion journal writeback",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("--file", required=True)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--mode", choices=["step","auto"], default="step")
    ap.add_argument("--speed", type=float, default=5.0)
    ap.add_argument("--qty", type=int, default=100)
    ap.add_argument("--fees", type=float, default=0.003)
    ap.add_argument("--orb-minutes", type=int, default=5)
    ap.add_argument("--risk-cents", type=float, default=20.0)
    ap.add_argument("--max-qty", type=int, default=200)
    ap.add_argument("--force-exit", action="store_true", help="Force close any open position on the final bar")
    ap.add_argument("--no-notion", action="store_true")
    args = ap.parse_args()

    token = os.environ.get("NOTION_TOKEN","").strip()
    db_id = os.environ.get("NOTION_DB_ID","").strip()

    df = load_bars(args.file)
    print(f"[replay] {args.symbol} mode={args.mode} speed={args.speed} file={args.file}")
    res = run_replay(df=df, symbol=args.symbol, mode=args.mode, speed=args.speed,
                     fees_per_share=args.fees, orb_minutes=args.orb_minutes,
                     risk_cents=args.risk_cents, max_qty=args.max_qty,
                     force_exit=args.force_exit)
    print(f"[result] bars={res.bars} trades={res.trades} pnl={res.pnl} entry={res.entry_px} exit={res.exit_px} pos={res.final_pos}")

    if args.no_notion: return
    if not token or not (token.startswith("ntn_") or token.startswith("secret_")):
        print("ERROR: NOTION_TOKEN env missing/malformed.", file=sys.stderr); sys.exit(2)
    if not db_id or len(db_id) < 32:
        print("ERROR: NOTION_DB_ID env missing.", file=sys.stderr); sys.exit(2)

    notion = NotionClient(token)
    schema = fetch_schema(notion, db_id)
    notes = textwrap.dedent(f"""
    Replay Session
    - Symbol: {args.symbol}
    - Mode: {args.mode} @ {args.speed} bars/sec
    - ORB minutes: {args.orb_minutes}, risk_cents: {args.risk_cents}, max_qty: {args.max_qty}
    - Bars: {res.bars}, Trades: {res.trades}, Theoretical PnL: {res.pnl}
    """).strip()
    props = build_replay_properties(schema, name=f"Replay {args.symbol} ORB ({args.mode})",
                                    symbol=args.symbol, qty=args.qty,
                                    entry_px=res.entry_px, exit_px=res.exit_px,
                                    fees=args.fees, kelly_f=None, notes=notes, extras=None)
    try:
        page = notion.pages_create(db_id, properties=props)
        print(f"[notion] session logged: page_id={{page.get('id','')}}")
    except requests.HTTPError as e:
        print(f"[notion] create failed: {e} :: {(getattr(e,'response',None) and e.response.text)}", file=sys.stderr)
        sys.exit(3)

if __name__ == "__main__":
    main()
