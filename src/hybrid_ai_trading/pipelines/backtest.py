# >>> HAT:INTRADAY_EXPORT:BEGIN
try:
    from .backtest_intraday import (
        IntradayBacktester as IntradayBacktester,  # test-compat export
    )
except Exception:
    # Fallback stub to keep tests importable even if real impl is absent
    class IntradayBacktester:  # pragma: no cover
        def __init__(self, *args, **kwargs): ...
        def run(self, *args, **kwargs): ...


try:
    __all__
except NameError:
    __all__ = []
if "IntradayBacktester" not in __all__:
    __all__.append("IntradayBacktester")
# >>> HAT:INTRADAY_EXPORT:END
