from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

# best-effort imports
try:
    from hybrid_ai_trading.utils.config import load_yaml_with_env as load_cfg
except Exception:
    import yaml

    def load_cfg(p: str) -> dict:
        with open(p, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}


# optional risk factory
def build_risk(cfg: dict):
    try:
        from hybrid_ai_trading.runners.paper_risk_factory import build_risk_stack

        return build_risk_stack(cfg)
    except Exception:
        return None


# local qc adapter (mirrors paper_trader._qc_run_once)
def qc_like_run(symbols, snapshots, cfg, logger):
    # try paper_trader adapter first
    try:
        from hybrid_ai_trading.runners import paper_trader as PT

        fn = getattr(PT, "_qc_run_once", None)
        if callable(fn):
            return fn(symbols, snapshots, cfg, logger)
    except Exception:
        pass
    # fallback: call quantcore.run_once in multiple signatures
    try:
        import hybrid_ai_trading.runners.paper_quantcore as qc
    except Exception as e:
        logger_info(logger, "once_done", note=f"quantcore missing: {e}", result={"items": []})
        return {"items": []}
    # 1) (cfg, logger, snapshots=...)
    try:
        return _norm(qc.run_once(cfg, logger, snapshots=snapshots))
    except TypeError:
        pass
    except Exception:
        pass
    # 2) (cfg, logger)
    try:
        return _norm(qc.run_once(cfg, logger))
    except TypeError:
        pass
    except Exception:
        pass
    # 3) (symbols, price_map, risk_mgr)
    price_map = {}
    try:
        price_map = {
            s.get("symbol"): s.get("price")
            for s in (snapshots or [])
            if isinstance(s, dict) and s.get("symbol")
        }
    except Exception:
        price_map = {}
    risk_mgr = (cfg or {}).get("risk_mgr")
    try:
        return _norm(qc.run_once(list(symbols or []), dict(price_map or {}), risk_mgr))
    except Exception as e:
        logger_info(
            logger, "once_done", note=f"quantcore run_once failed: {e}", result={"items": []}
        )
        return {"items": []}


def _norm(result):
    if isinstance(result, dict):
        return result if "items" in result or "decisions" in result else {"items": []}
    if isinstance(result, list):
        return {
            "summary": {"rows": len(result), "batches": 1, "decisions": len(result)},
            "items": result,
        }
    return {"items": []}


def logger_info(logger, evt, **kw):
    try:
        logger.info(evt, **kw)
    except Exception:
        pass


def riskhub_checks(snapshots, result, logger):
    try:
        from hybrid_ai_trading.utils.risk_client import RISK_HUB_URL, check_decision
    except Exception as e:
        logger_info(logger, "risk_checks", items=[], note=f"risk_client_unavailable: {e}")
        return
    price_map = {}
    try:
        price_map = {
            s.get("symbol"): s.get("price")
            for s in (snapshots or [])
            if isinstance(s, dict) and s.get("symbol")
        }
    except Exception:
        price_map = {}
    checks = []
    iterable = (result or {}).get("items") or (result or {}).get("decisions") or []
    for d in iterable:
        sym = d.get("symbol") if isinstance(d, dict) else None
        dec = (
            d.get("decision")
            if (isinstance(d, dict) and "decision" in d)
            else (d if isinstance(d, dict) else {})
        )
        ks = (dec or {}).get("kelly_size") or {}
        try:
            qty = float(ks.get("qty") or dec.get("qty") or 0.0)
        except Exception:
            qty = 0.0
        px = float(price_map.get(sym) or 0.0)
        notion = qty * px
        try:
            resp = check_decision(RISK_HUB_URL, sym or "", qty, notion, str(dec.get("side", "BUY")))
        except Exception as e:
            resp = {"error": str(e)}
        checks.append(
            {"symbol": sym, "qty": qty, "price": px, "notional": notion, "response": resp}
        )
    logger_info(logger, "risk_checks", items=checks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default="AAPL,MSFT")
    ap.add_argument("--log-file", default="logs/phase4_paper_smoke.jsonl")
    ap.add_argument("--config", default="config/paper_runner.yaml")
    args = ap.parse_args()

    # universe
    symbols = [s.strip() for s in (args.universe or "").split(",") if s.strip()]
    # logger
    from hybrid_ai_trading.runners.paper_logger import JsonlLogger

    Path(os.path.dirname(args.log_file) or ".").mkdir(parents=True, exist_ok=True)
    logger = JsonlLogger(args.log_file)

    # cfg + risk
    try:
        cfg = load_cfg(args.config)
    except Exception as e:
        cfg = {}
        logger_info(logger, "config_error", path=args.config, error=str(e))
    rm = build_risk(cfg)
    if rm is not None:
        cfg = dict(cfg)
        cfg["risk_mgr"] = rm

    logger_info(logger, "run_start", cfg=cfg, symbols=symbols, note="phase4_smoke")

    # provider-only snapshots (no IB)
    snapshots = [{"symbol": s, "price": None} for s in symbols]
    res = qc_like_run(symbols, snapshots, cfg, logger)
    riskhub_checks(snapshots, res, logger)
    logger_info(logger, "once_done", note="phase4_smoke complete", result=res)
    print("WROTE", args.log_file)


if __name__ == "__main__":
    main()
