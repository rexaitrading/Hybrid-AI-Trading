# -*- coding: utf-8 -*-
from __future__ import annotations
import os, time
from typing import List

from ib_insync import Stock
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
    symbols: List[str] = []
    try:
        base = cfg.get("universe", []) or cfg.get("equities", [])
        if isinstance(base, str):
            base = [x.strip() for x in base.split(",") if x.strip()]
        if isinstance(base, list):
            symbols.extend([str(x).strip() for x in base if str(x).strip()])
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
    """
    Main paper session:
      1) Load config and merge universe
      2) Preflight safety (strict or forced)
      3) IB session -> build snapshots -> QuantCore evaluate
    """
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

    # Strict skip when CLOSED and not forced
    if not probe["session"]["ok_time"] and not force:
        print(f"Market closed ({probe['session']['session']}), skipping trading window.")
        return 0

    logger = JsonlLogger(getattr(args, "log_file", "logs/runner_paper.jsonl"))
    logger.info("preflight", probe=probe, universe=symbols)

    loop_cfg = (cfg.get("loop") or {}) if isinstance(cfg, dict) else {}
    try:
        sleep_sec = int(loop_cfg.get("sleep_sec", 5))
    except Exception:
        sleep_sec = 5

    # Drill handling:
    # - If CLOSED and forced but snapshots_when_closed=False -> drill only (skip second IB session)
    # - If CLOSED and forced and snapshots_when_closed=True  -> continue to snapshots + QuantCore
    if not probe["session"]["ok_time"] and force and not getattr(args, "snapshots_when_closed", False):
        logger.info("drill_only", note="market closed; forced preflight ran; skipping second IB session")
        return 0

    # ---- IB connection & QuantCore snapshots ----
    with ib_session() as ib:
        apply_mdt(ib, getattr(args, "mdt", 3))
        acct = probe.get("account")
        logger.info("ib_connected", account=acct, symbols=symbols)

        # Build live snapshots for all symbols
        contracts = {sym: Stock(sym, "SMART", "USD") for sym in symbols}
        for c in contracts.values():
            ib.reqMktData(c, "", False, False)
        ib.sleep(1.5)

        def _snap(sym: str):
            c = contracts[sym]
            t = ib.ticker(c)
            price = t.last or t.marketPrice() or getattr(t, "close", None) or getattr(t, "vwap", None) or None
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

        # Import QuantCore runner
        from hybrid_ai_trading.runners.paper_quantcore import run_once

        snapshots = [_snap(sym) for sym in symbols]

        if getattr(args, "once", False):
            result = run_once(cfg, logger, snapshots=snapshots)
            logger.info("once_done", note="single pass complete", result=result)
            return 0

        while True:
            snapshots = [_snap(sym) for sym in symbols]
            result = run_once(cfg, logger, snapshots=snapshots)
            # RiskHub checks (log-only; no order placement here)
from hybrid_ai_trading.utils.risk_client import check_decision, RISK_HUB_URL
price_map = { s.get("symbol"): s.get("price") for s in snapshots if isinstance(s, dict) }
checks = []
for d in (result or {}).get("decisions", []):
    sym = d.get("symbol")
    qty = 0.0
    ks  = d.get("kelly_size") or {}
    try:
        qty = float(ks.get("qty") or d.get("qty") or 0)
    except Exception:
        qty = 0.0
    px  = 0.0
    try:
        px = float(price_map.get(sym) or 0)
    except Exception:
        px = 0.0
    notion = qty * px
    resp = check_decision(RISK_HUB_URL, sym or "", qty, notion, "BUY")
    checks.append({"symbol": sym, "qty": qty, "price": px, "notional": notion, "response": resp})
logger.info("risk_checks", items=checks)
logger.info("decision_snapshot", result=result)
            ib.sleep(sleep_sec)
            if os.environ.get("STOP_PAPER_LOOP", "0") == "1":
                logger.info("loop_stop", note="STOP_PAPER_LOOP env detected")
                break

    return 0