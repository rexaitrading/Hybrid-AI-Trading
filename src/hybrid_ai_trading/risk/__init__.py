"""
hybrid_ai_trading.risk package
- Lazy exports to avoid import-time cycles & side-effects
- No eager imports (esp. patch_api)
"""

def get_RiskManager():
    """
    Lazy accessor to avoid import-time loops.

    Usage:
        from hybrid_ai_trading.risk import get_RiskManager
        RiskManager = get_RiskManager()
    """
    from .risk_manager import RiskManager as _RM
    return _RM

def __getattr__(name):
    # PEP 562: lazy attribute access for top-level symbols
    if name == "RiskManager":
        from .risk_manager import RiskManager
        return RiskManager
    # Optionally: fallback to submodules (GateScore, SentimentFilter, etc.)
    # Only import on demand; keep this very lightweight.
    try:
        import importlib
        mod = importlib.import_module(f"{__name__}.{name}")
        return mod
    except Exception as _e:
        raise AttributeError(name)

__all__ = ["get_RiskManager", "RiskManager"]
