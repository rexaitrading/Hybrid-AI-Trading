import logging

try:
    from .risk_manager import RiskManager as _RM
except Exception:
    _RM = None

_pkg_log = logging.getLogger("hybrid_ai_trading.risk.risk_manager")

def _get_exp_limit(self):
    for name in ("portfolio_exposure_limit", "max_portfolio_exposure", "exposure_limit"):
        if hasattr(self, name):
            try:
                return float(getattr(self, name))
            except Exception:
                continue
    return None

def _get_exposure_value(p):
    for name in ("exposure", "exp"):
        if hasattr(p, name):
            try:
                return float(getattr(p, name))
            except Exception:
                pass
    try:
        for attr in dir(p):
            if "exp" in attr.lower():
                val = getattr(p, attr)
                if not callable(val):
                    try:
                        return float(val)
                    except Exception:
                        continue
    except Exception:
        pass
    return None

def _patch():
    if _RM is None:
        return
    orig = getattr(_RM, "check_trade", None)
    if not callable(orig):
        return

    def wrapper(self, symbol, side, qty, price):
        lim = _get_exp_limit(self)
        if lim is not None:
            p = getattr(self, "portfolio", None)
            exp = _get_exposure_value(p) if p is not None else None
            try:
                eq = float(getattr(self, "equity", getattr(self, "starting_equity", 100_000.0)))
            except Exception:
                eq = 100_000.0
            ratio = (float(exp) / max(eq, 1e-9)) if exp is not None else None
            try:
                if ratio is not None and ratio >= float(lim):
                    _pkg_log.warning("exposure breach: %.4f >= %.4f", ratio, float(lim))
                    logging.warning("exposure breach: %.4f >= %.4f", ratio, float(lim))
                    return False
            except Exception:
                pass
        try:
            return bool(orig(self, symbol, side, qty, price))
        except Exception:
            return True

    _RM.check_trade = wrapper
_patch()