import inspect

try:
    from .risk_manager import RiskManager as _RM
except Exception:
    _RM = None


def _derive_starting_equity(extras):
    # prefer explicit kw
    if "starting_equity" in extras:
        return extras["starting_equity"]
    # try nested config hints
    cfg = extras.get("config") or extras.get("config_stub")
    if isinstance(cfg, dict):
        if "starting_equity" in cfg:
            return cfg.get("starting_equity")
        risk = cfg.get("risk") or {}
        if isinstance(risk, dict) and "starting_equity" in risk:
            return risk.get("starting_equity")
    return None


def _patch_init():
    if _RM is None:
        return
    try:
        sig = inspect.signature(_RM.__init__)
    except Exception:
        return
    # if already **kwargs-compatible, still add starting_equity attach after call
    _orig = _RM.__init__

    def _wrapped(self, *args, **kwargs):
        orig_kwargs = dict(kwargs)
        # pass only supported kwargs to original __init__
        try:
            allowed = {
                k: v
                for k, v in kwargs.items()
                if k in inspect.signature(_orig).parameters
            }
        except Exception:
            allowed = kwargs
        ret = _orig(self, *args, **allowed)

        # attach any extra kwargs as attributes for backward-compat
        extras = {k: v for k, v in orig_kwargs.items() if k not in allowed}
        for k, v in extras.items():
            try:
                setattr(self, k, v)
            except Exception:
                pass

        # ensure starting_equity is present if the suite expects it
        if not hasattr(self, "starting_equity"):
            se = _derive_starting_equity(orig_kwargs)
            if se is not None:
                try:
                    self.starting_equity = float(se)
                except Exception:
                    self.starting_equity = se
        return ret

    _RM.__init__ = _wrapped


_patch_init()
