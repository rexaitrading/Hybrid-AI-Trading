# -*- coding: utf-8 -*-
from __future__ import annotations
import os, time, json, yaml
from typing import Optional, List

from ib_insync import IB, Stock
from hybrid_ai_trading.utils.ib_conn import ib_session
from hybrid_ai_trading.utils.preflight import sanity_probe
from hybrid_ai_trading.runners.paper_utils import apply_mdt
from hybrid_ai_trading.runners.paper_logger import JsonlLogger
from hybrid_ai_trading.runners.paper_config import load_config

ALLOW_TRADE_WHEN_CLOSED = os.environ.get("ALLOW_TRADE_WHEN_CLOSED","0") == "1"

# ---------------------------------------------------------------------------
# Utility: build trading universe from YAML + CLI override
# ---------------------------------------------------------------------------
def build_universe(cfg: dict, override: str = "") -> list[str]:
    symbols = []
    try:
        base = cfg.get("universe", [])
        if isinstance(base, str):
            base = [x.strip() for x in base.split(",") if x.strip()]
        symbols.extend(base)
    except Exception:
        pass
    if override:
        for x in override.split(","):
            x = x.strip()
            if x and x not in symbols:
                symbols.append(x)
    return symbols

# ---------------------------------------------------------------------------
# Core session
# ---------------------------------------------------------------------------
def run_paper_session(args) -> int:
    """Main paper session: config load -> preflight -> trading loop"""
    # ---- Load YAML config ----
    cfg_path = getattr(args, "config", "config/paper_runner.yaml")
    try:
        cfg = load_config(cfg_path)
    except Exception as e:
        print(f"[CONFIG] Failed to load {cfg_path}: {e}")
        cfg = {}

    symbols = build_universe(cfg, getattr(args, "universe", ""))
    if not symbols:
        print("[CONFIG] Universe empty -> nothing to trade.")
        return 0

    # ---- Preflight ----
    force = bool(ALLOW_TRADE_WHEN_CLOSED or getattr(args, "dry_drill", False))
    probe = sanity_probe(symbol="AAPL", qty=1, cushion=0.10,
                         allow_ext=True, force_when_closed=force)
    if not probe.get("ok"):
        raise RuntimeError(f"Preflight failed: {probe}")
    if not probe["session"]["ok_time"] and not force:
        print(f"Market closed ({probe['session']['session']}), skipping trading window.")
        return 0

    logger = JsonlLogger(getattr(args, "log_file", "logs/runner_paper.jsonl"))
    logger.info("preflight", probe=probe, universe=symbols)

    # Drill-only path
    if not probe["session"]["ok_time"] and force:
        logger.info("drill_only", note="market closed; forced preflight ran; skipping second IB session")
        return 0

    # ---- IB connection & trading loop ----
    with ib_session() as ib:
        apply_mdt(ib, getattr(args, "mdt", 3))
        acct = probe.get("account")
        logger.info("ib_connected", account=acct, symbols=symbols)

        # Example: fetch last prices
        for sym in symbols:
            c = Stock(sym, "SMART", "USD")
            ib.reqMktData(c, "", False, False)
        ib.sleep(2.0)
        for sym in symbols:
            c = Stock(sym, "SMART", "USD")
            t = ib.ticker(c)
            px = t.last or t.marketPrice() or t.close or None
            logger.info("price_snapshot", symbol=sym, price=px)

                        # --- QuantCore v3: build live snapshots then evaluate ---
        from hybrid_ai_trading.runners.paper_quantcore import run_once

        # Request quotes for all symbols
        contracts = {sym: Stock(sym, "SMART", "USD") for sym in symbols}
        for c in contracts.values():
            ib.reqMktData(c, "", False, False)
        ib.sleep(1.5)

        def _snap(sym):
            c = contracts[sym]
            t = ib.ticker(c)
            # robust price pick
            price = t.last or t.marketPrice() or t.close or t.vwap or None
            return {
                "symbol": sym,
                "price": float(price) if price is not None else None,
                "bid": float(t.bid) if t.bid is not None else None,
                "ask": float(t.ask) if t.ask is not None else None,
                "last": float(t.last) if t.last is not None else None,
                "close": float(getattr(t, "close", None)) if getattr(t, "close", None) is not None else None,
                "vwap": float(getattr(t, "vwap", None)) if getattr(t, "vwap", None) is not None else None,
                "volume": float(getattr(t, "volume", 0.0) or 0.0),
                "ts": ib.serverTime().isoformat() if hasattr(ib, "serverTime") else None,
            }

        snapshots = [_snap(sym) for sym in symbols]

        if getattr(args, "once", False):
            result = run_once(cfg, logger, snapshots=snapshots)
            logger.info("once_done", note="single pass complete", result=result)
            return 0

        while True:
            snapshots = [_snap(sym) for sym in symbols]
            result = run_once(cfg, logger, snapshots=snapshots)
            logger.info("decision_snapshot", result=result)
            ib.sleep(5)
            if os.environ.get("STOP_PAPER_LOOP", "0") == "1":
                logger.info("loop_stop", note="STOP_PAPER_LOOP env detected")
                break

        while True:
            for sym in symbols:
                logger.info("heartbeat", symbol=sym)
            ib.sleep(5)
            # Placeholder: break condition
            if os.environ.get("STOP_PAPER_LOOP","0") == "1":
                logger.info("loop_stop", note="STOP_PAPER_LOOP env detected")
                break

    return 0

