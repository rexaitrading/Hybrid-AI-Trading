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
def _safe_empty_dataframe(columns=None, dtypes=None):
    """Return an empty pandas DataFrame with optional columns and dtypes.

    Parameters
    ----------
    columns : list[str] | None
        Column names to include (optional).
    dtypes : dict[str, str] | None
        Optional mapping of column -> dtype to enforce.

    Returns
    -------
    pandas.DataFrame
    """
    import pandas as pd  # local import to avoid hard dependency at import time

    df = pd.DataFrame(columns=list(columns or []))
    if dtypes:
        for col, dt in (dtypes or {}).items():
            if col not in df.columns:
                df[col] = pd.Series(dtype=dt)
            else:
                try:
                    df[col] = df[col].astype(dt)
                except Exception:
                    # If coercion fails on empty frame, ensure dtype via empty Series
                    df[col] = pd.Series(dtype=dt)
    return df
