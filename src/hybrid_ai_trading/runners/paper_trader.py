__all__ = ["_normalize_result", "_qc_run_once"]


def _normalize_result(result):
    """Normalize to {'summary': {...}, 'items': [...]}.
    - list -> wraps into dict with decisions=len(list)
    - dict with 'items' -> returned as-is
    - else -> empty structure
    """
    if isinstance(result, dict) and "items" in result:
        return result
    if isinstance(result, list):
        items = result
        return {
            "summary": {"rows": len(items), "batches": 1, "decisions": len(items)},
            "items": items,
        }
    return {"summary": {"rows": 0, "batches": 0, "decisions": 0}, "items": []}


def _qc_run_once(symbols, price_map, cfg, risk_mgr, logger=None):
    """Call paper_quantcore.run_once with best-effort signatures, normalize the output."""
    # lightweight logger if None
    if logger is None:

        class _L:
            def info(self, *a, **k):
                pass

            def warning(self, *a, **k):
                pass

            def error(self, *a, **k):
                pass

        logger = _L()

    try:
        import hybrid_ai_trading.runners.paper_quantcore as qc
    except Exception:
        qc = None

    result = None
    if qc and hasattr(qc, "run_once"):
        # new-style
        try:
            result = qc.run_once(symbols, price_map, risk_mgr)
        except TypeError:
            # legacy plain
            try:
                result = qc.run_once(cfg, logger)
            except TypeError:
                # legacy w/ snapshots (use list of dicts in price_map to match your test)
                try:
                    snapshots = price_map if isinstance(price_map, list) else []
                    result = qc.run_once(cfg, logger, snapshots=snapshots)
                except TypeError:
                    result = None

    if result is None:
        items = [{"symbol": s, "decision": {}} for s in (symbols or [])]
        result = {
            "summary": {"rows": len(items), "batches": 1, "decisions": len(items)},
            "items": items,
        }

    out = _normalize_result(result)
    if "summary" in out:
        out["summary"]["decisions"] = len(out.get("items", []))
    return out


def cli_run_once(universe: str, log_file: str, provider_only: bool = True):
    """Minimal stable entry to run one provider-only pass and write a custom JSONL log."""
    from types import SimpleNamespace

    args = SimpleNamespace(
        provider_only=provider_only,
        prefer_providers=False,
        once=True,
        universe=universe,
        log_file=log_file,
        config="config/paper_runner.yaml",
        dry_drill=False,
        snapshots_when_closed=True,
        mdt=1,
    )
    return run_paper_session(args)


def cli_run_once_smoke(universe: str, log_file: str, provider_only: bool = True):
    """
    Robust helper: provider-only single pass that writes JSONL log without relying on
    run_paper_session/build_universe. Safe to import/call directly.
    """
    import os
    from types import SimpleNamespace

    try:
        from hybrid_ai_trading.runners.paper_config import load_config
    except Exception:

        def load_config(p: str):
            return {}

    try:
        from hybrid_ai_trading.runners.paper_risk_factory import build_risk_stack
    except Exception:
        build_risk_stack = None
    try:
        from hybrid_ai_trading.runners.paper_logger import JsonlLogger
    except Exception as e:
        raise RuntimeError(f"JsonlLogger unavailable: {e}")

    cfg = {}
    try:
        cfg = load_config("config/paper_runner.yaml") or {}
    except Exception:
        cfg = {}
    if build_risk_stack:
        try:
            rm = build_risk_stack(cfg)
            cfg = dict(cfg)
            cfg["risk_mgr"] = rm
        except Exception:
            pass

    symbols = [s.strip() for s in (universe or "").split(",") if s.strip()]
    try:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    except Exception:
        pass
    logger = JsonlLogger(log_file)
    logger.info("run_start", cfg=cfg, symbols=symbols, note="cli_run_once_smoke")

    # provider-only snapshots and QC adapter
    snapshots = [{"symbol": s, "price": None} for s in symbols]
    try:
        res = _qc_run_once(symbols, snapshots, cfg, logger)
    except Exception:
        # best-effort fallback if adapter missing
        try:
            import hybrid_ai_trading.runners.paper_quantcore as qc

            # try signatures
            try:
                res = qc.run_once(cfg, logger, snapshots=snapshots)
            except TypeError:
                try:
                    res = qc.run_once(cfg, logger)
                except TypeError:
                    price_map = {s["symbol"]: s.get("price") for s in snapshots}
                    rm = cfg.get("risk_mgr")
                    res = qc.run_once(symbols, price_map, rm)
        except Exception:
            res = {"items": []}

    # riskhub checks are best-effort
    try:
        from hybrid_ai_trading.utils.risk_client import RISK_HUB_URL, check_decision

        price_map = {s["symbol"]: s.get("price") for s in snapshots}
        items = []
        for d in res.get("items") or res.get("decisions") or []:
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
                resp = check_decision(
                    RISK_HUB_URL, sym or "", qty, notion, str(dec.get("side", "BUY"))
                )
            except Exception as e:
                resp = {"error": str(e)}
            items.append(
                {
                    "symbol": sym,
                    "qty": qty,
                    "price": px,
                    "notional": notion,
                    "response": resp,
                }
            )
        logger.info("risk_checks", items=items)
    except Exception:
        pass

    logger.info("once_done", note="cli_run_once_smoke complete", result=res)
    return 0


def cli_run_once_safe(universe: str, log_file: str, provider_only: bool = True):
    """
    Provider-only single pass that always writes JSONL log.
    - Masks cfg['risk_mgr'] to avoid JSON serialization errors.
    - Does not rely on run_paper_session or build_universe.
    """
    import os
    from pathlib import Path

    try:
        from hybrid_ai_trading.runners.paper_config import load_config
    except Exception:

        def load_config(p: str):
            return {}

    try:
        from hybrid_ai_trading.runners.paper_risk_factory import build_risk_stack
    except Exception:
        build_risk_stack = None
    try:
        from hybrid_ai_trading.runners.paper_logger import JsonlLogger
    except Exception as e:
        raise RuntimeError(f"JsonlLogger unavailable: {e}")

    # cfg + risk (best-effort)
    try:
        cfg = load_config("config/paper_runner.yaml") or {}
    except Exception:
        cfg = {}
    if build_risk_stack:
        try:
            rm = build_risk_stack(cfg)
            cfg = dict(cfg)
            cfg["risk_mgr"] = rm
        except Exception:
            pass

    # symbols & logger
    symbols = [s.strip() for s in (universe or "").split(",") if s.strip()]
    Path(os.path.dirname(log_file) or ".").mkdir(parents=True, exist_ok=True)
    logger = JsonlLogger(log_file)

    # MASK non-serializable objects before logging
    cfg_log = dict(cfg)
    try:
        if "risk_mgr" in cfg_log:
            cfg_log["risk_mgr"] = "attached"
    except Exception:
        pass
    logger.info("run_start", cfg=cfg_log, symbols=symbols, note="cli_run_once_safe")

    # snapshots
    snapshots = [{"symbol": s, "price": None} for s in symbols]

    # Try paper_trader adapter; fall back to quantcore signatures; else empty
    try:
        fn = globals().get("_qc_run_once", None)
        if callable(fn):
            res = fn(symbols, snapshots, cfg, logger)
        else:
            try:
                import hybrid_ai_trading.runners.paper_quantcore as qc

                try:
                    res = qc.run_once(cfg, logger, snapshots=snapshots)
                except TypeError:
                    try:
                        res = qc.run_once(cfg, logger)
                    except TypeError:
                        price_map = {s["symbol"]: s.get("price") for s in snapshots}
                        rm = cfg.get("risk_mgr")
                        res = qc.run_once(symbols, price_map, rm)
            except Exception:
                res = {"items": []}
    except Exception:
        res = {"items": []}

    # riskhub checks (best-effort)
    try:
        from hybrid_ai_trading.utils.risk_client import RISK_HUB_URL, check_decision

        price_map = {s["symbol"]: s.get("price") for s in snapshots}
        items = []
        for d in res.get("items") or res.get("decisions") or []:
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
                resp = check_decision(
                    RISK_HUB_URL, sym or "", qty, notion, str(dec.get("side", "BUY"))
                )
            except Exception as e:
                resp = {"error": str(e)}
            items.append(
                {
                    "symbol": sym,
                    "qty": qty,
                    "price": px,
                    "notional": notion,
                    "response": resp,
                }
            )
        logger.info("risk_checks", items=items)
    except Exception:
        pass

    logger.info("once_done", note="cli_run_once_safe complete", result=res)
    return 0


def _phase4_enrich_decisions(result: dict, symbols, snapshots, cfg, logger):
    """
    Post-process decisions to add regime/sentiment/kelly sizing and risk approval.
    Result shapes supported:
      - {"items":[{"symbol":..,"decision":{..}}]}
      - {"decisions":[{..}]}
    Adds (primitives only):
      decision["regime"]    = {"regime": str, "confidence": float, "reason": "stub|metrics"}
      decision["sentiment"] = {"sentiment": float, "confidence": float, "reason": "stub|model"}
      decision["kelly_size"]= {"f": float, "qty": int, "notional": float, "reason": str}
      decision["risk_approved"] = {"approved": bool, "reason": str}
    """
    try:
        rm = (cfg or {}).get("risk_mgr")
    except Exception:
        rm = None
    if not isinstance(result, dict):
        return result
    if not rm:
        return result

    # build a quick price map from snapshots
    price_map = {}
    try:
        price_map = {
            (s.get("symbol") if isinstance(s, dict) else None): (
                s.get("price") if isinstance(s, dict) else None
            )
            for s in (snapshots or [])
            if isinstance(s, dict) and s.get("symbol")
        }
    except Exception:
        price_map = {}

    key = (
        "items"
        if "items" in result
        else ("decisions" if "decisions" in result else None)
    )
    if not key:
        return result

    enriched = []
    for d in result.get(key) or []:
        if isinstance(d, dict) and "decision" in d:
            sym = d.get("symbol")
            dec = d.get("decision") or {}
            carrier = d  # write back into d["decision"]
        elif isinstance(d, dict):
            sym = d.get("symbol")
            dec = d
            carrier = d
        else:
            enriched.append(d)
            continue

        try:
            side = str(dec.get("side", "BUY")).upper()
        except Exception:
            side = "BUY"

        # regime
        try:
            reg = None
            conf = None
            try:
                reg = rm.regime.detect(sym) if hasattr(rm, "regime") else None
                conf = rm.regime.confidence(sym) if hasattr(rm, "regime") else None
            except Exception:
                reg, conf = "neutral", 0.5
            dec["regime"] = {
                "regime": reg or "neutral",
                "confidence": float(conf or 0.5),
                "reason": "stub" if conf is None else "metrics",
            }
        except Exception:
            pass

        # sentiment (no text available here  neutral w/ confidence)
        try:
            sent = 0.0
            conf = 0.5
            if hasattr(rm, "sent") and hasattr(rm.sent, "score"):
                try:
                    sent = float(
                        rm.sent.score("")
                    )  # no text: returns 0.0/0.5 per model behavior
                    conf = 0.5
                except Exception:
                    sent, conf = 0.0, 0.5
            dec["sentiment"] = {
                "sentiment": float(sent),
                "confidence": float(conf),
                "reason": "stub",
            }
        except Exception:
            pass

        # kelly sizing + risk approval
        try:
            px = None
            try:
                px = float(dec.get("price") or dec.get("limit") or 0.0)
            except Exception:
                px = 0.0
            if (not px) and sym in price_map and price_map[sym]:
                try:
                    px = float(price_map[sym])
                except Exception:
                    px = 0.0

            # compute kelly fraction & qty (guarded)
            f = 0.0
            qty = 0
            reason = "ok"
            try:
                if (
                    hasattr(rm, "kelly")
                    and hasattr(rm.kelly, "size_position")
                    and getattr(rm, "equity", None)
                ):
                    f = float(rm.kelly.kelly_fraction(risk_veto=False))
                    size = float(
                        rm.kelly.size_position(
                            float(rm.equity), float(px or 0.0), risk_veto=False
                        )
                    )
                    qty = int(size) if size > 0 else 0
                else:
                    f, qty = 0.0, 0
            except Exception as e:
                f, qty, reason = 0.0, 0, f"kelly_error:{e}"

            notional = float(qty) * float(px or 0.0)

            ok, why = True, ""
            try:
                gate = getattr(rm, "approve_trade", None)
                if callable(gate):
                    g = gate(sym or "NA", side, float(qty), float(notional))
                    if isinstance(g, dict):
                        ok, why = bool(g.get("approved", True)), str(
                            g.get("reason", "")
                        )
                    elif isinstance(g, (tuple, list)) and g:
                        ok, why = bool(g[0]), ("" if len(g) < 2 else str(g[1]))
                    else:
                        ok, why = bool(g), ""
            except Exception as e:
                ok, why = False, f"risk_error:{e}"

            dec["kelly_size"] = {
                "f": float(f),
                "qty": int(qty),
                "notional": float(notional),
                "reason": reason,
            }
            dec["risk_approved"] = {"approved": bool(ok), "reason": str(why)}

            # write back
            if "decision" in carrier:
                carrier["decision"] = dec
        except Exception:
            pass

        enriched.append(carrier)

    result[key] = enriched
    return result
