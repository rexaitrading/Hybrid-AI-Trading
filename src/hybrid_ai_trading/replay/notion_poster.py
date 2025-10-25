from __future__ import annotations
import os, csv, time, json, argparse, hashlib, sys
from typing import Dict, Any, List, Optional

try:
    import requests
except Exception as _e:
    print("[notion] 'requests' missing. Install with: pip install requests")
    raise

"""
Notion Poster:
- Reads a CSV (replay_journal.csv or replay_journal.sim.csv).
- Upserts each row as a page in a Notion database.
- Idempotent via local map and 'external_id' property (add a Text prop to your DB).

Env:
  NOTION_TOKEN = secret_xxx
  NOTION_DB_ID = 32-char db id
"""

NOTION_TOKEN = os.environ.get("NOTION_TOKEN") or ""
NOTION_DB_ID = os.environ.get("NOTION_DB_ID") or ""

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

MAP_PATH = "logs/notion_posted_ids.json"  # local upsert map

def _load_map() -> Dict[str,str]:
    if os.path.exists(MAP_PATH):
        try:
            return json.load(open(MAP_PATH,"r",encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save_map(m: Dict[str,str]):
    os.makedirs(os.path.dirname(MAP_PATH) or ".", exist_ok=True)
    tmp = MAP_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
    os.replace(tmp, MAP_PATH)

def _ext_id(row: Dict[str,str]) -> str:
    # Stable unique key from row content: ts|symbol|side|qty|price
    key = "|".join([
        row.get("ts",""), row.get("symbol",""),
        (row.get("side","") or "").upper(),
        str(row.get("qty","")),
        str(row.get("price","")),
        str(row.get("entry_px","")),  # sim columns may exist
        str(row.get("exit_px","")),
    ])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()

def _notion_props(row: Dict[str,str]) -> Dict[str,Any]:
    # Map CSV columns to Notion property payloads.
    # Expected DB props: ts (Date), symbol (Title or Text), price (Number),
    # setup (Select), side (Select), qty (Number), kelly_f (Number),
    # confidence (Number), reason (Rich text), regime (Select), sentiment (Number/Text),
    # notes (Rich text), entry_px/exit_px/gross_pnl/slippage/fees/net_pnl (Numbers),
    # external_id (Text).
    def num(k: str) -> Optional[float]:
        v = row.get(k, "")
        try:
            return float(v)
        except Exception:
            return None
    def text(v: str) -> Dict[str,Any]:
        return {"rich_text":[{"type":"text","text":{"content": v[:1900]}}]} if v else {"rich_text":[]}

    symbol = row.get("symbol","")
    title_val = f"{row.get('ts','')}  {symbol}  {row.get('side','')}"
    props = {
        "Name": {"title":[{"type":"text","text":{"content": title_val[:1900]}}]},  # optional "Name" title; adjust to your DB
        "symbol": {"rich_text":[{"type":"text","text":{"content": symbol}}]},
        "ts": {"date":{"start": row.get("ts","") or None}},
        "price": {"number": num("price")},
        "setup": {"select": {"name": row.get("setup","")}} if row.get("setup") else None,
        "side": {"select": {"name": (row.get("side","") or "").upper()}} if row.get("side") else None,
        "qty": {"number": num("qty")},
        "kelly_f": {"number": num("kelly_f")},
        "confidence": {"number": num("confidence")},
        "reason": text(row.get("reason","")),
        "regime": {"select": {"name": row.get("regime","")}} if row.get("regime") else None,
        "sentiment": {"rich_text":[{"type":"text","text":{"content": row.get("sentiment","")}}]} if row.get("sentiment") else {"rich_text":[]},
        "notes": text(row.get("notes","")),
        "entry_px": {"number": num("entry_px")},
        "exit_px": {"number": num("exit_px")},
        "gross_pnl": {"number": num("gross_pnl")},
        "slippage": {"number": num("slippage")},
        "fees": {"number": num("fees")},
        "net_pnl": {"number": num("net_pnl")},
        "external_id": {"rich_text":[{"type":"text","text":{"content": _ext_id(row)}}]},
    }
    # Drop None properties
    return {k:v for k,v in props.items() if v is not None}

def _create_page(db_id: str, props: Dict[str,Any]) -> Optional[str]:
    url = "https://api.notion.com/v1/pages"
    payload = {"parent":{"database_id": db_id},"properties": props}
    r = requests.post(url, headers=HEADERS, data=json.dumps(payload))
    if r.status_code in (200, 201):
        return r.json().get("id")
    # Debug print trimmed
    try:
        j = r.json()
    except Exception:
        j = {"text": r.text}
    print(f"[notion] create failed {r.status_code}: {str(j)[:2000]}")
    return None

def _update_page(page_id: str, props: Dict[str,Any]) -> bool:
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {"properties": props}
    r = requests.patch(url, headers=HEADERS, data=json.dumps(payload))
    if r.status_code in (200, 201):
        return True
    try:
        j = r.json()
    except Exception:
        j = {"text": r.text}
    print(f"[notion] update failed {r.status_code}: {str(j)[:2000]}")
    return False

def poster_main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="logs/replay_journal.sim.csv", help="Source CSV (use replay_journal.csv or .sim.csv)")
    ap.add_argument("--db-id", default=os.environ.get("NOTION_DB_ID",""))
    ap.add_argument("--token", default=os.environ.get("NOTION_TOKEN",""))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--simulate", action="store_true", help="Dry run: build payloads but do not POST")
    ap.add_argument("--rate", type=float, default=3.0, help="max req/sec (Notion ~3rps).")
    args = ap.parse_args()

    if not args.db_id or not args.token:
        print("[notion] Missing NOTION_DB_ID or NOTION_TOKEN (env or args).")
        return 2

    # refresh headers in case token passed as arg
    global HEADERS
    HEADERS = {
        "Authorization": f"Bearer {args.token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    if not os.path.exists(args.csv):
        print(f"[notion] CSV not found: {args.csv}")
        return 2

    with open(args.csv, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("[notion] CSV is empty.")
        return 0

    posted_map = _load_map()
    rate_sleep = 1.0/max(0.1, args.rate)

    sent, updated, skipped = 0, 0, 0
    for i, row in enumerate(rows):
        if args.limit and sent+updated+skipped >= args.limit:
            break

        eid = _ext_id(row)
        props = _notion_props(row)

        if args.simulate:
            print(f"[simulate] would upsert external_id={eid} symbol={row.get('symbol')} ts={row.get('ts')}")
            continue

        if eid in posted_map:
            # Update existing page
            ok = _update_page(posted_map[eid], props)
            if ok:
                updated += 1
            else:
                print(f"[notion] warn: update failed eid={eid}")
        else:
            pid = _create_page(args.db_id, props)
            if pid:
                posted_map[eid] = pid
                sent += 1
            else:
                print(f"[notion] warn: create failed eid={eid}")
        _save_map(posted_map)
        time.sleep(rate_sleep)

    print(f"[notion] done. created={sent} updated={updated} skipped={skipped} total_seen={len(rows)}")
    return 0

if __name__ == "__main__":
    sys.exit(poster_main())
