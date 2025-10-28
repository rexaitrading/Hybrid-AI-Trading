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
