from __future__ import annotations

# -*- coding: utf-8 -*-
import os
import time
import types
from typing import List, Dict, Any

from ib_insync import Stock
from hybrid_ai_trading.utils.ib_conn import ib_session
from hybrid_ai_trading.utils.preflight import sanity_probe
from hybrid_ai_trading.runners.paper_utils import apply_mdt
from hybrid_ai_trading.runners.paper_logger import JsonlLogger
from hybrid_ai_trading.runners.paper_config import load_config
import hybrid_ai_trading.runners.paper_quantcore as qc

ALLOW_TRADE_WHEN_CLOSED = os.environ.get("ALLOW_TRADE_WHEN_CLOSED", "0") == "1"


def _normalize_result(result):
    """Return a canonical dict: {'summary': {...}, 'items': [...]}."""
    try:
        if isinstance(result, dict):
            return result
        if isinstance(result, list):
            items = result
            return {
                "summary": {"rows": len(items), "batches": 1, "decisions": len(items)},
                "items": items,
            }
    except Exception:
        pass
    return {"summary": {"rows": 0, "batches": 0, "decisions": 0}, "items": []}


def _qc_run_once(symbols, snapshots, cfg, logger):
    """Call quantcore.run_once with maximum compatibility, normalized to dict."""
    try:
        fn = getattr(qc, "run_once", None)
    except Exception:
        fn = None
    if fn is None:
        raise RuntimeError("quantcore.run_once not found")

    # 1) legacy (cfg, logger, snapshots=...)
    try:
        return _normalize_result(fn(cfg, logger, snapshots=snapshots))
    except TypeError:
        pass
    except Exception:
        pass

    # 2) legacy (cfg, logger)
    try:
        return _normalize_result(fn(cfg, logger))
    except TypeError:
        pass
    except Exception:
        pass

    # 3) new style (symbols, price_map, risk_mgr)
    price_map = {}
    try:
        price_map = {
            (s.get("symbol") if isinstance(s, dict) else None):
            (s.get("price") if isinstance(s, dict) else None)
            for s in (snapshots or [])
            if isinstance(s, dict) and s.get("symbol")
        }
    except Exception:
        price_map = {}

    risk_mgr = None
    if isinstance(cfg, dict):
        for k in ("risk_mgr", "risk_manager", "risk"):
            try:
                if cfg.get(k) is not None:
                    risk_mgr = cfg.get(k)
                    break
            except Exception:
                pass
    if risk_mgr is None:
        # inline stub object avoids nested class indentation issues
        risk_mgr = types.SimpleNamespace(
            approve_trade=lambda *a, **k: {"approved": True, "reason": "stub"}
        )

    return _normalize_result(fn(list(symbols or []), dict(price_map or {}), risk_mgr))


def build_universe(cfg: Dict[str, Any], override: str = "") -> list[str]:
    symbols: List[str] = []
    try:
        base = (cfg.get("universe") if isinstance(cfg, dict) else None) or \
               (cfg.get("equities") if isinstance(cfg, dict) else None) or []
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


def _riskhub_checks(snapshots, result, logger):
    """Call RiskHub for each decision; log-only (no order placement)."""
    try:
        from hybrid_ai_trading.utils.risk_client import check_decision, RISK_HUB_URL
    except Exception as e:
        logger.info("risk_checks", items=[], note=f"risk_client_unavailable: {e}")
        return

    # build price map
    price_map = {}
    try:
        price_map = {
            (s.get("symbol") if isinstance(s, dict) else None):
            (s.get("price") if isinstance(s, dict) else None)
            for s in (snapshots or [])
            if isinstance(s, dict) and s.get("symbol")
        }
    except Exception:
        price_map = {}

    checks = []
    # support both {"items":[{"symbol":..,"decision":{..}}]} and {"decisions":[...]}
    iterable = (result or {}).get("items") or (result or {}).get("decisions") or []
    for d in iterable:
        if isinstance(d, dict) and "decision" in d:
            sym = d.get("symbol")
            dec = d.get("decision") or {}
        else:
            sym = d.get("symbol") if isinstance(d, dict) else None
            dec = d if isinstance(d, dict) else {}
        ks  = dec.get("kelly_size") or {}
        try:
            qty = float(ks.get("qty") or dec.get("qty") or 0.0)
        except Exception:
            qty = 0.0
        try:
            px = float(price_map.get(sym) or 0.0)
        except Exception:
            px = 0.0
        notion = qty * px
        resp = check_decision(RISK_HUB_URL, sym or "", qty, notion, "BUY")
        checks.append({"symbol": sym, "qty": qty, "price": px, "notional": notion, "response": resp})
    logger.info("risk_checks", items=checks)


def run_paper_session(args) -> int:
    """
    Main paper session:
      1) Load config and merge universe
      2) Preflight safety (strict or forced)
      3) IB session -> snapshots -> QuantCore evaluate
    """
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
    probe = sanity_probe(symbol="AAPL", qty=1, cushion=0.10, allow_ext=True, force_when_closed=force)
    if not probe.get("ok"):
        raise RuntimeError(f"Preflight failed: {probe}")

    if not probe["session"]["ok_time"] and not force:
        print(f"Market closed ({probe['session']['session']}), skipping trading window.")
        return 0

    logger = JsonlLogger(getattr(args, "log_file", "logs/runner_paper.jsonl"))
    logger.info("preflight", probe=probe, universe=symbols)

    # Drill handling (snapshots_when_closed lets us proceed)
    if not probe["session"]["ok_time"] and force and not getattr(args, "snapshots_when_closed", False):
        logger.info("drill_only", note="market closed; forced preflight ran; skipping second IB session")
        return 0

    with ib_session() as ib:
        apply_mdt(ib, getattr(args, "mdt", 3))
        acct = probe.get("account")
        logger.info("ib_connected", account=acct, symbols=symbols)

        # loop cadence from YAML
        loop_cfg = (cfg.get("loop") or {}) if isinstance(cfg, dict) else {}
        try:
            sleep_sec = int(loop_cfg.get("sleep_sec", 5))
        except Exception:
            sleep_sec = 5

        # Subscribe & snapshot helper
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

        snapshots = [_snap(sym) for sym in symbols]

        # -------- once mode --------
        if getattr(args, "once", False):
            result = _qc_run_once(symbols, snapshots, cfg, logger)
            _riskhub_checks(snapshots, result, logger)

            # enforce RiskHub (paper-safe)
            if getattr(args, "enforce_riskhub", False):
                try:
                    from hybrid_ai_trading.utils.risk_client import check_decision, RISK_HUB_URL
                except Exception:
                    def check_decision(*a, **k): return {"ok": False, "reason":"risk_client_unavailable"}
                    RISK_HUB_URL = "http://127.0.0.1:8787"

                price_map = {
                    (s.get("symbol") if isinstance(s, dict) else None): (s.get("price") if isinstance(s, dict) else None)
                    for s in (snapshots or []) if isinstance(s, dict) and s.get("symbol")
                }
                denied = []
                for d in (result or {}).get("items", []):
                    sym = d.get("symbol")
                    dec = d.get("decision") or {}
                    ks  = dec.get("kelly_size") or {}
                    try: qty = float(ks.get("qty") or dec.get("qty") or 0.0)
                    except: qty = 0.0
                    try: px = float(price_map.get(sym) or 0.0)
                    except: px = 0.0
                    notion = qty * px
                    resp = check_decision(RISK_HUB_URL, sym or "", qty, notion, "BUY")
                    if not resp.get("ok", False):
                        denied.append({"symbol": sym, "qty": qty, "price": px, "notional": notion, "response": resp})
                if denied:
                    logger.info("risk_enforced_denied", items=denied)
                    return 0

            logger.info("once_done", note="single pass complete", result=result)
            return 0

        # -------- continuous loop --------
        while True:
            snapshots = [_snap(sym) for sym in symbols]
            result = _qc_run_once(symbols, snapshots, cfg, logger)

            _riskhub_checks(snapshots, result, logger)
            logger.info("decision_snapshot", result=result)

            if getattr(args, "enforce_riskhub", False):
                try:
                    from hybrid_ai_trading.utils.risk_client import check_decision, RISK_HUB_URL
                except Exception:
                    def check_decision(*a, **k): return {"ok": False, "reason":"risk_client_unavailable"}
                    RISK_HUB_URL = "http://127.0.0.1:8787"

                price_map = {
                    (s.get("symbol") if isinstance(s, dict) else None): (s.get("price") if isinstance(s, dict) else None)
                    for s in (snapshots or []) if isinstance(s, dict) and s.get("symbol")
                }
                denied = []
                for d in (result or {}).get("items", []):
                    sym = d.get("symbol")
                    dec = d.get("decision") or {}
                    ks  = dec.get("kelly_size") or {}
                    try: qty = float(ks.get("qty") or dec.get("qty") or 0.0)
                    except: qty = 0.0
                    try: px = float(price_map.get(sym) or 0.0)
                    except: px = 0.0
                    notion = qty * px
                    resp = check_decision(RISK_HUB_URL, sym or "", qty, notion, "BUY")
                    if not resp.get("ok", False):
                        denied.append({"symbol": sym, "qty": qty, "price": px, "notional": notion, "response": resp})
                if denied:
                    logger.info("risk_enforced_denied", items=denied)
                    ib.sleep(sleep_sec)
                    continue

            ib.sleep(sleep_sec)
            if os.environ.get("STOP_PAPER_LOOP", "0") == "1":
                logger.info("loop_stop", note="STOP_PAPER_LOOP env detected")
                break

    return 0