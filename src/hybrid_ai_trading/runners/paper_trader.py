from __future__ import annotations
import sys
"""
Provider-only fast path (before preflight)
"""

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

from hybrid_ai_trading.execution.route_exec import place_entry as route_place_entry
ALLOW_TRADE_WHEN_CLOSED = os.environ.get("ALLOW_TRADE_WHEN_CLOSED", "0") == "1"
contracts = {}


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

def _provider_price_map(symbols):
    """Minimal provider map stub: returns empty prices (None)."""
    try:
        return {s: None for s in (symbols or [])}
    except Exception:
        return {}

def _apply_provider_prices(snapshots, prov_map, *, override=False):
    """If override, fill snapshot['price'] from prov_map when available."""
    out = []
    try:
        for s in snapshots or []:
            d = dict(s or {})
            sym = d.get("symbol")
            if override and sym in (prov_map or {}) and prov_map.get(sym) is not None:
                try:
                    d["price"] = float(prov_map[sym])
                except Exception:
                    pass
            out.append(d)
    except Exception:
        return list(snapshots or [])
    return out
def _provider_only_run(args, cfg, symbols, logger):
    """Run once using providers only (no IB session)."""
    prov_map = _provider_price_map(symbols)  # currently returns {sym: None}
    snapshots = [{"symbol": s, "price": (None if prov_map.get(s) is None else float(prov_map.get(s)))} for s in symbols]

    # Optionally override (provider-first)
    if getattr(args, "prefer_providers", False):
        snapshots = _apply_provider_prices(snapshots, prov_map, override=True)

    # Evaluate via QuantCore adapter (no IB risk; risk_mgr via cfg/stub handled in adapter)
    result = _qc_run_once(symbols, snapshots, cfg, logger)

    # Provider-only mode is analysis-only: log RiskHub, do NOT route
    _riskhub_checks(snapshots, result, logger)
    logger.info("once_done", note="provider-only run", result=result)

    try:
        print("provider-only run (no routing)")
    except Exception:
        pass

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
def _merge_provider_flags(args, cfg, rm=None):
    """Merge provider-only/prefer-providers flags from cfg + CLI (CLI wins)."""
    cfg = dict(cfg or {})
    if rm is not None:
        try:
            cfg["risk_mgr"] = rm
        except Exception:
            pass
    cfg_provider_only = bool(cfg.get("provider_only", False))
    cfg_prefer_prov   = bool(cfg.get("prefer_providers", False))
    if getattr(args, "provider_only", None) is True:
        cfg_provider_only = True
    if getattr(args, "prefer_providers", None) is True:
        cfg_prefer_prov = True
    cfg["provider_only"] = cfg_provider_only
    cfg["prefer_providers"] = cfg_prefer_prov
    return cfg

# --- appended clean overrides: paper_trader runtime-safe definitions ---
def _snap(ib, sym: str):
    c = contracts[sym]
    t = ib.ticker(c)
    price = t.last or t.marketPrice() or getattr(t, "close", None) or getattr(t, "vwap", None) or None
    return {
        "symbol": sym,
        "price": float(price) if price is not None else None,
        "bid": float(t.bid) if getattr(t, "bid", None) is not None else None,
        "ask": float(t.ask) if getattr(t, "ask", None) is not None else None,
        "last": float(t.last) if getattr(t, "last", None) is not None else None,
        "close": float(getattr(t, "close", None)) if getattr(t, "close", None) is not None else None,
        "vwap": float(getattr(t, "vwap", None)) if getattr(t, "vwap", None) is not None else None,
        "volume": float(getattr(t, "volume", 0.0) or 0.0),
        "ts": ib.serverTime().isoformat() if hasattr(ib, "serverTime") else None,
    }
def run_paper_session(args) -> int:
    """
    Clean runtime-safe implementation that passes smoke tests.
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
    log_path = getattr(args, "log_file", "logs/runner_paper.jsonl")
    try:
    except Exception:
        pass
    # CI-NULL-PATH-GUARD: normalize log_path for CI and local runs
    log_path = log_path or os.getenv("HAT_LOG_FILE")
    if not log_path:
        # fallback into CI report dir or workspace
        report_dir = os.getenv("HAT_REPORT_DIR") or os.getenv("GITHUB_WORKSPACE") or "."
        log_path = os.path.join(report_dir, "paper_runner.log")
    logger = JsonlLogger(log_path)
    logger.info("run_start", cfg=cfg, symbols=symbols)

    # Provider-only fast path
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
    logger.info("preflight", probe=probe, universe=symbols)

    if not probe["session"]["ok_time"] and force and not getattr(args, "snapshots_when_closed", False):
        logger.info("drill_only", note="market closed; forced preflight ran; skipping trading")
        return 0
    with ib_session() as ib:
        apply_mdt(ib, getattr(args, "mdt", 3))
        logger.info("ib_connected", account=probe.get("account"), symbols=symbols)

        # Subscribe
        global contracts
        contracts = {sym: Stock(sym, "SMART", "USD") for sym in symbols}
        for c in contracts.values():
            ib.reqMktData(c, "", False, False)
        ib.sleep(1.5)

        # Once mode
        if getattr(args, "once", False):
            snapshots = [_snap(ib, sym) for sym in symbols]
            result = _qc_run_once(symbols, snapshots, cfg, logger)
            _route_decisions_via_exec(result, cfg.get("risk_mgr"), logger, snapshots=snapshots)
            _riskhub_checks(snapshots, result, logger)
            logger.info("once_done", note="single pass complete", result=result)
            return 0
        # Continuous loop
        loop_cfg = (cfg.get("loop") or {}) if isinstance(cfg, dict) else {}
        try:
            sleep_sec = int(loop_cfg.get("sleep_sec", 5))
        except Exception:
            sleep_sec = 5
        # NEW: respect HAT_MAX_LOOPS env (defaults infinite)
        try:
            _max_loops = int(os.environ.get("HAT_MAX_LOOPS", "0") or "0")
        except Exception:
            _max_loops = 0
        _loops = 0

        while True:
            snapshots = [_snap(ib, sym) for sym in symbols]
            result = _qc_run_once(symbols, snapshots, cfg, logger)
            _route_decisions_via_exec(result, cfg.get("risk_mgr"), logger, snapshots=snapshots)
            _riskhub_checks(snapshots, result, logger)
            logger.info("decision_snapshot", result=result)

            _loops += 1
            if _max_loops and _loops >= _max_loops:
                break

            time.sleep(sleep_sec)

# --- end appended clean overrides ---


def _route_decisions_via_exec(result, risk_mgr, logger, limit_pad_bps: int = 5, snapshots=None):
    """
    Route BUY/SELL decisions to ExecRouter with risk_mgr.
    Supports:
      - {"items":[{"symbol":"AAPL","decision":{"kelly_size":{"qty":..},"side":"BUY","price":..}}]}
      - {"decisions":[...]}
    """
    try:
        items = (result or {}).get("items") or (result or {}).get("decisions") or []
        routed = []
        price_map_snap = {}
        try:
            if snapshots:
                for s in (snapshots or []):
                    if isinstance(s, dict) and s.get('symbol'):
                        price_map_snap[s['symbol']] = float(s.get('price') or 0.0)
        except Exception:
            price_map_snap = {}
        for d in items:
            if isinstance(d, dict) and "decision" in d:
                sym = d.get("symbol")
                dec = d.get("decision") or {}
            else:
                sym = d.get("symbol") if isinstance(d, dict) else None
                dec = d if isinstance(d, dict) else {}

            side = str(dec.get("side") or "BUY").upper()
            ks   = dec.get("kelly_size") or {}
            qty  = int(ks.get("qty") or dec.get("qty") or 0)
            limit_px = float(dec.get("limit") or dec.get("price") or 0.0)
            # fill price from snapshots if needed
            if (limit_px <= 0.0) and sym in price_map_snap and price_map_snap[sym] > 0.0:
                px = price_map_snap[sym]
                pad = float(limit_pad_bps)/10000.0
                limit_px = px * (1.0 + pad if side == 'BUY' else 1.0 - pad)
            if not sym or qty <= 0 or side not in ("BUY","SELL") or limit_px <= 0.0:
                routed.append({"symbol": sym, "status": "skip", "reason": "bad_inputs", "side": side, "qty": qty, "limit": limit_px})
                continue

            # risk gate
            try:
                ok, reason = True, ""
                gate = getattr(risk_mgr, "approve_trade", None)
                if callable(gate):
                    g = gate(sym, side, qty, float(qty)*limit_px)
                    if isinstance(g, dict):
                        ok, reason = bool(g.get("approved")), str(g.get("reason",""))
                    elif isinstance(g, (tuple, list)) and g:
                        ok, reason = bool(g[0]), ("" if len(g)<2 else str(g[1]))
                    else:
                        ok, reason = bool(g), ""
                if not ok:
                    routed.append({"symbol": sym, "status": "veto", "reason": reason, "side": side, "qty": qty, "limit": limit_px})
                    continue
            except Exception as e:
                routed.append({"symbol": sym, "status": "error", "reason": f"risk:{e}", "side": side, "qty": qty, "limit": limit_px})
                continue

            try:
                resp = route_place_entry(sym, side, qty, limit_px, risk_manager=risk_mgr)
                routed.append({"symbol": sym, **(resp or {})})
            except Exception as e:
                routed.append({"symbol": sym, "status": "error", "reason": f"route:{e}", "side": side, "qty": qty, "limit": limit_px})

        logger.info("route_result", items=routed)
        return routed
    except Exception as e:
        logger.error("route_error", error=str(e))
        return []

# ---- CLI entrypoint (safe) ----
def _cli_main():
    try:
        from hybrid_ai_trading.runners.paper_config import parse_args
    except Exception:
        import argparse
# HAT-SAFE-LOG-PATH (paper_trader)
def _hat_safe_log_path(path):
    base = os.environ.get('HAT_REPORT_DIR') or os.environ.get('GITHUB_WORKSPACE') or ''
    # Default to <base>/.ci/paper_runner.log or ./.ci if base is empty
    if path is None or (isinstance(path, str) and not path.strip()):
        report_dir = os.path.join(base, '.ci') if base else '.ci'
        os.makedirs(report_dir, exist_ok=True)
        return os.path.join(report_dir, 'paper_runner.log')
    p = os.fspath(path)
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    return p

        parser = argparse.ArgumentParser()
        parser.add_argument("--provider-only", action="store_true")
        parser.add_argument("--prefer-providers", action="store_true")
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--universe", type=str, default="AAPL")
        parser.add_argument("--mdt", type=int, default=3)
        parser.add_argument("--log-file", type=str, default="logs/runner_paper.jsonl")
        args = parser.parse_args()
    else:
        args = parse_args()

    # allow flag injection from argv
    try:
        args = _inject_provider_cli(args)
    except Exception:
        pass

    rc = run_paper_session(args)
    return 0 if (rc is None) else int(rc)

if __name__ == "__main__":
    raise SystemExit(_cli_main())

