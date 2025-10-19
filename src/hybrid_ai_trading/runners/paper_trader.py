"""
Provider-only fast path (before preflight)
"""
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
def _norm_approval(a):
    try:
        if isinstance(a, dict):
            return {"approved": bool(a.get("approved")), "reason": str(a.get("reason",""))}
        if isinstance(a, (tuple, list)) and a:
            ok = bool(a[0]); rs = "" if len(a)<2 else str(a[1])
            return {"approved": ok, "reason": rs}
        if isinstance(a, bool):
            return {"approved": a, "reason": ""}
    except Exception:
        pass
    return {"approved": False, "reason": "normalize_error"}
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
def _provider_only_run(args, cfg, symbols, logger):
    """Run once using providers only (no IB session)."""
    prov_map = _provider_price_map(symbols)
    # synth "snapshots"
    snapshots = [{"symbol": s, "price": (None if prov_map.get(s) is None else float(prov_map.get(s)))} for s in symbols]
    # Optionally override (provider-first)\r
        snapshots = _apply_provider_prices(snapshots, prov_map, override=True)
    # Evaluate via QuantCore adapter (no IB risk; risk_mgr via cfg/stub handled in adapter)
    result = _qc_run_once(symbols, snapshots, cfg, logger)
    _riskhub_checks(snapshots, result, logger)
    logger.info("once_done", note="provider-only run", result=result)
    print("provider-only run")
    return 0
def _inject_provider_cli(args):
    """
    Ensure CLI flags work even if the main parser didn't define them.
    If "--provider-only"/"--prefer-providers" appear in sys.argv,
    set args.provider_only / args.prefer_providers when missing.
    """
    try:
        argv = sys.argv or []
    except Exception:
        return args
    if "--provider-only" in argv and not hasattr(args, "provider_only"):
        try:
            setattr(args, "provider_only", True)
        except Exception:
            pass
    if "--prefer-providers" in argv and not hasattr(args, "prefer_providers"):
        try:
            setattr(args, "prefer_providers", True)
        except Exception:
            pass
    return args
def _merge_provider_flags(args, cfg):
    """Merge provider-only/prefer-providers flags from cfg + CLI (CLI wins)."""
    cfg = dict(cfg or {})
try:
    cfg["risk_mgr"] = rm
except NameError:
    pass  # risk_mgr injection skipped if rm not defined yet
    cfg_provider_only = bool(cfg.get("provider_only", False))
    cfg_prefer_prov   = bool(cfg.get("prefer_providers", False))
    # CLI (or shim) wins:
    if getattr(args, "provider_only", None) is True:
        cfg_provider_only = True
    if getattr(args, "prefer_providers", None) is True:
        cfg_prefer_prov = True
    cfg["provider_only"] = cfg_provider_only
    cfg["prefer_providers"] = cfg_prefer_prov
    return cfg


def run_paper_session(args) -> int:
    """
    poll_sec = cfg.get('poll_sec', 2)
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

        # Provider-only mode fast path
        if getattr(args, "provider_only", False):
            return _provider_only_run(args, cfg, symbols, logger)

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
                "close": float(getattr(t, "close", None))\r
        if getattr(t, "close", None) is not None else None,
                "vwap": float(getattr(t, "vwap", None))\r
        if getattr(t, "vwap", None) is not None else None,
                "volume": float(getattr(t, "volume", 0.0) or 0.0),
                "ts": ib.serverTime().isoformat() if hasattr(ib, "serverTime") else None,
            }

        snapshots = [_snap(sym) for sym in symbols]

        # -------- once mode --------
        if getattr(args, "once", False):
            result = _qc_run_once(symbols, snapshots, cfg, logger)
            _riskhub_checks(snapshots, result, logger)

            # enforce RiskHub (paper-safe)\r
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

            # ---- executor (DRY_RUN guarded) ----
            if os.environ.get('DRY_RUN','1') == '0':
                try:
                    from hybrid_ai_trading.execution.route_exec import place_entry
                    decs = (result or {}).get('items', [])
                    for d in decs:
                        sym = d.get('symbol')
                        dec = d.get('decision') or {}
                        ks  = dec.get('kelly_size') or {}
                        try:
                            qty = int(ks.get('qty') or dec.get('qty') or 0)
                        except Exception:
                            qty = 0
                        try:
                            px  = float(dec.get('limit_px') or dec.get('px') or 0.0)
                        except Exception:
                            px  = 0.0
                        side = str(dec.get('side') or 'BUY').upper()
                        if sym and qty > 0 and px > 0.0:
                            resp = place_entry(sym, side, qty, px)
                            logger.info('exec_place', symbol=sym, side=side, qty=qty, px=px, resp=resp)
                except Exception as _e:
                    logger.error('exec_error', extra={'error': str(_e)})\r
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
import sys
import yaml


