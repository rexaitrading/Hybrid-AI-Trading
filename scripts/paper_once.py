from __future__ import annotations

import argparse
import os
import pathlib
import sys
from typing import Any, Dict, List

# --- import bootstrap so running as a file or as -m works the same ---
_THIS_DIR = pathlib.Path(__file__).resolve().parent
_ROOT = _THIS_DIR.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import hybrid_ai_trading.runners.paper_trader as M
from hybrid_ai_trading.runners.paper_logger import JsonlLogger
from ib_insync import IB, Stock

# guardrails (package absolute import)
try:
    from scripts.guardrails import clamp_universe, load_guardrails, vet_and_adjust
except ModuleNotFoundError:
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    from scripts.guardrails import clamp_universe, load_guardrails, vet_and_adjust

MICRO_KEYS = ("price", "bid", "ask", "bidSize", "askSize", "volume")


def ib_snapshots(symbols: List[str]) -> List[Dict[str, Any]]:
    ib = IB()
    ib.connect("127.0.0.1", 4002, clientId=17, timeout=15)
    contracts = {s: Stock(s, "SMART", "USD") for s in symbols}
    for c in contracts.values():
        ib.reqMktData(c, "", False, False)
    ib.sleep(1.5)
    out: List[Dict[str, Any]] = []
    for s in symbols:
        t = ib.ticker(contracts[s])
        px = t.last or t.marketPrice() or getattr(t, "close", None) or getattr(t, "vwap", None)
        bid = getattr(t, "bid", None)
        ask = getattr(t, "ask", None)
        bsize = getattr(t, "bidSize", None)
        asize = getattr(t, "askSize", None)
        vol = getattr(t, "volume", None)
        try:
            fpx = float(px) if px is not None else None
            fbid = float(bid) if bid is not None else None
            fask = float(ask) if ask is not None else None
        except Exception:
            fpx, fbid, fask = None, None, None
        out.append(
            {
                "symbol": s,
                "price": fpx,
                "bid": fbid,
                "ask": fask,
                "bidSize": bsize,
                "askSize": asize,
                "volume": vol,
            }
        )
    ib.disconnect()
    return out


def _enrich_with_snapshots(
    items: List[Dict[str, Any]], snap_map: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Merge microstructure fields from snapshots into each decision dict."""
    enriched = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        sym = it.get("symbol")
        dec = dict(it.get("decision") or {})
        snap = snap_map.get(sym) or {}
        for k in MICRO_KEYS:
            if k not in dec and k in snap:
                dec[k] = snap[k]
        it["decision"] = dec
        enriched.append(it)
    return enriched


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider-only", action="store_true")
    ap.add_argument("--once", action="store_true", default=True)  # CLI parity
    ap.add_argument("--universe", type=str, default="AAPL,MSFT")
    ap.add_argument("--log-file", type=str, default="logs/runner_paper.jsonl")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.log_file) or ".", exist_ok=True)
    logger = JsonlLogger(args.log_file)

    # Universe + guardrail clamp
    symbols = [s.strip() for s in args.universe.split(",") if s.strip()]
    g = load_guardrails()
    symbols = clamp_universe(symbols, g)

    if not symbols:
        logger.info("run_start", note="universe empty", symbols=[])
        print("[CONFIG] Universe empty -> nothing to trade.")
        return 0

    # Snapshot source
    if args.provider_only:
        snapshots = [{"symbol": s, "price": None} for s in symbols]
        mode = "provider-only-shim"
    else:
        snapshots = ib_snapshots(symbols)
        mode = "ib-once-shim"

    cfg = {"provider_only": bool(args.provider_only)}

    # Log start
    logger.info("run_start", mode=mode, symbols=symbols, snapshots=snapshots)

    # QuantCore adapter
    result: Dict[str, Any] = M._qc_run_once(symbols, snapshots, cfg, logger) or {}

    # ---- Ensure 1:1 coverage: backfill any missing symbols with explicit stubs ----
    got_syms = {
        (it.get("symbol") if isinstance(it, dict) else None) for it in (result.get("items") or [])
    }
    missing = [s for s in symbols if s not in got_syms]
    if missing:
        stubs = []
        for s in missing:
            stubs.append(
                {
                    "symbol": s,
                    "decision": {
                        "setup": "unknown",
                        "regime": {
                            "regime": "unknown",
                            "confidence": 0.0,
                            "reason": "missing_from_qc",
                        },
                        "sentiment": {
                            "sentiment": 0.0,
                            "confidence": 0.0,
                            "reason": "missing_from_qc",
                        },
                        "kelly_size": {"f": 0.0, "qty": 0, "reason": "missing_from_qc"},
                        "risk_approved": {"approved": False, "reason": "missing_from_qc"},
                    },
                }
            )
        result["items"] = (result.get("items") or []) + stubs
        logger.info("qc_backfill", missing=missing, note="added stub decisions for dropped symbols")

    # hard invariant: 1:1 coverage
    assert len(result.get("items", [])) == len(symbols), "coverage_invariant_failed"

    # ---- Enrich each decision with microstructure BEFORE vetting ----
    snap_map = {d["symbol"]: d for d in snapshots if isinstance(d, dict) and "symbol" in d}
    result["items"] = _enrich_with_snapshots(result.get("items") or [], snap_map)

    # Guardrails patch per item (force risk_approved True on OK)
    try:
        items = result.get("items") or []
        patched = []
        for it in items:
            if not isinstance(it, dict):
                continue
            sym = it.get("symbol")
            dec = dict(it.get("decision") or {})
            ok, rsn, dec2 = vet_and_adjust(sym, dec, g)
            if ok:
                dec2["risk_approved"] = {"approved": True, "reason": rsn}
            else:
                dec2["risk_approved"] = {"approved": False, "reason": rsn}
            it["decision"] = dec2
            patched.append(it)
        if patched:
            result["items"] = patched
    except Exception as _e:
        logger.info("guardrails_error", error=str(_e))

    # Log finish + stdout summary
    logger.info("once_done", result=result)
    print(f"{mode}: items:", len(result.get("items", [])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
