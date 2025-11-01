from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from typing import Dict, Iterable, List


# ---------- Strategies ----------
def orb_scalper_v1(bars: Iterable[Dict]) -> List[Dict]:
    """
    Toy ORB-style breakout for demo:
    - Tracks session high/low
    - After 30 bars, BUY on breakout of session high
    - TP = +0.35, SL = -0.25, qty = 1
    """
    trades: List[Dict] = []
    session_high = None
    session_low = None
    qty = 1

    for b in bars:
        ts = b["ts"]
        px = float(b["close"])
        session_high = px if session_high is None else max(session_high, px)
        session_low = px if session_low is None else min(session_low, px)

        if b["i"] > 30 and px >= session_high:
            entry = px
            stop = entry - 0.25
            take = entry + 0.35
            exit_px = take  # assume instant fill for demo
            pnl = (exit_px - entry) * qty
            rr = (take - entry) / (entry - stop) if (entry - stop) > 0 else 0.0

            trades.append(
                {
                    "symbol": b["symbol"],
                    "side": "BUY",
                    "qty": qty,
                    "entry_px": round(entry, 2),
                    "exit_px": round(exit_px, 2),
                    "pnl": round(pnl, 2),
                    "rr": round(rr, 2),
                    "ts_entry": ts,
                    "ts_exit": ts,
                    "strategy": "orb_scalper_v1",
                    "regime": "Neutral",
                    "sentiment": "Neutral",
                    "notes": "Demo auto-take-profit",
                }
            )
    return trades


STRATS = {"orb_scalper_v1": orb_scalper_v1}

# ---------- Utilities ----------
REQUIRED_COLS = {"open", "high", "low", "close"}
ANY_TS_COLS = ("timestamp", "ts", "time")


def read_csv_bars(path: str, symbol: str) -> List[Dict]:
    if not os.path.exists(path):
        raise SystemExit(f"CSV not found: {path}")

    with open(path, newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            raise SystemExit("CSV has no header row")

        headers = {h.strip().lower() for h in r.fieldnames}
        if not REQUIRED_COLS.issubset(headers):
            raise SystemExit(
                f"CSV missing columns: need {sorted(REQUIRED_COLS)}; got {sorted(headers)}"
            )

        ts_key = None
        for k in ANY_TS_COLS:
            if k in headers:
                ts_key = k
                break
        if not ts_key:
            raise SystemExit(f"CSV needs one timestamp column: {ANY_TS_COLS}")

        bars: List[Dict] = []
        for i, row in enumerate(r):
            # normalize keys to lower
            row_l = {k.strip().lower(): v for k, v in row.items()}
            try:
                bars.append(
                    {
                        "i": i,
                        "symbol": symbol,
                        "ts": row_l.get(ts_key),
                        "open": float(row_l["open"]),
                        "high": float(row_l["high"]),
                        "low": float(row_l["low"]),
                        "close": float(row_l["close"]),
                        "volume": float(row_l.get("volume") or 0.0),
                    }
                )
            except Exception as e:
                raise SystemExit(f"Bad row {i}: {e}")
        return bars


def notion_create_page(db_id: str, trade: Dict) -> Dict:
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise SystemExit("NOTION_TOKEN not set")

    def title(text: str) -> Dict:
        return {"title": [{"type": "text", "text": {"content": text}}]}

    def rich(text: str) -> Dict:
        return {"rich_text": [{"type": "text", "text": {"content": text}}]}

    def number(x: float) -> Dict:
        return {"number": float(x)}

    def date(s: str) -> Dict:
        return {"date": {"start": s}}

    def select(s: str) -> Dict:
        return {"select": {"name": s}}

    def checkbox(b: bool) -> Dict:
        return {"checkbox": bool(b)}

    props = {
        "Name": title(f"{trade['symbol']} {trade['strategy']} {trade['ts_entry']}"),
        "symbol": rich(trade["symbol"]),
        "side": select(trade["side"]),
        "qty": number(trade["qty"]),
        "entry_px": number(trade["entry_px"]),
        "exit_px": number(trade["exit_px"]),
        "gross_pnl": number(trade["pnl"]),
        "rr": number(trade["rr"]),
        "ts_entry": date(trade["ts_entry"]),
        "ts_exit": date(trade["ts_exit"]),
        "strategy": rich(trade["strategy"]),
        "regime": select(trade["regime"]),
        "sentiment": select(trade["sentiment"]),
        "journal": rich(trade.get("notes", "")),
        "is_theoretical": checkbox(True),
    }

    body = json.dumps({"parent": {"database_id": db_id}, "properties": props}).encode(
        "utf-8"
    )

    import urllib.request

    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--strategy", default="orb_scalper_v1")
    ap.add_argument(
        "--speed-ms", type=int, default=50
    )  # reserved for future realtime playback
    ap.add_argument("--notion-db")
    args = ap.parse_args()

    bars = read_csv_bars(args.csv, args.symbol)
    strat = STRATS.get(args.strategy)
    if not strat:
        raise SystemExit(f"Unknown strategy: {args.strategy}")

    trades = strat(bars)
    dry = os.environ.get("NO_NOTION") == "1" or not args.notion_db

    for t in trades:
        if dry:
            print(json.dumps({"dry_run_trade": t}, separators=(",", ":")))
        else:
            notion_create_page(args.notion_db, t)
            time.sleep(0.1)

    print(json.dumps({"trades": len(trades), "dry_run": dry}, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        # Preserve message, exit non-zero if error
        msg = str(e)
        if msg:
            print(msg, file=sys.stderr)
        code = e.code if isinstance(e.code, int) else (1 if msg else 0)
        sys.exit(code)
    except Exception as e:
        print(f"Unhandled error: {e}", file=sys.stderr)
        sys.exit(1)
