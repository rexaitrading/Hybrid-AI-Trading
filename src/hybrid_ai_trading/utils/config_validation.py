from __future__ import annotations
from typing import Any, Dict

from hybrid_ai_trading.risk.sentiment_filter import SentimentFilter

_ALLOWED_MODES = {"paper", "live"}

def _as_float(x: Any, name: str) -> float:
    try:
        return float(x)
    except Exception:
        raise ValueError(f"Invalid {name}: {x!r}")

def validate_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate & normalize top-level config.
    Raises ValueError with clear messages on bad inputs.
    Returns possibly-normalized cfg (shallow) for downstream.
    """
    if not isinstance(cfg, dict):
        raise ValueError("config must be a dict")

    out = dict(cfg)  # shallow copy

    # mode
    mode = str(out.get("mode", "paper")).lower()
    if mode not in _ALLOWED_MODES:
        raise ValueError(f"Invalid mode={mode!r}. Allowed: {_ALLOWED_MODES}")
    out["mode"] = mode

    # starting_equity (optional, if provided must be > 0)
    if "starting_equity" in out:
        se = _as_float(out["starting_equity"], "starting_equity")
        if se <= 0:
            raise ValueError(f"starting_equity must be > 0, got {se}")
        out["starting_equity"] = se

    # costs (optional)
    costs = out.get("costs", {})
    if isinstance(costs, dict):
        for k in ("commission_pct", "slippage_pct"):
            if k in costs:
                v = _as_float(costs[k], f"costs.{k}")
                if v < 0:
                    raise ValueError(f"costs.{k} must be >= 0, got {v}")
                costs[k] = v
        out["costs"] = costs

    # sentiment block
    sent = dict(out.get("sentiment", {})) if isinstance(out.get("sentiment", {}), dict) else {}
    model = str(sent.get("model", "vader")).lower()
    allowed = getattr(SentimentFilter, "_ALLOWED_MODELS", {"vader","hf","transformers","bert","distilbert"})
    if model not in allowed:
        raise ValueError(f"Invalid sentiment.model={model!r}. Allowed: {sorted(list(allowed))}")
    sent["model"] = model

    # thresholds [0,1]
    if "threshold" in sent:
        thr = _as_float(sent["threshold"], "sentiment.threshold")
        if not (0.0 <= thr <= 1.0):
            raise ValueError(f"sentiment.threshold must be in [0,1], got {thr}")
        sent["threshold"] = thr
    if "neutral_zone" in sent:
        nz = _as_float(sent["neutral_zone"], "sentiment.neutral_zone")
        if not (0.0 <= nz <= 1.0):
            raise ValueError(f"sentiment.neutral_zone must be in [0,1], got {nz}")
        sent["neutral_zone"] = nz

    out["sentiment"] = sent
    return out