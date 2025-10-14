from typing import Optional
from ib_insync import IB, util, Stock

def fetch_bars(
    ib: IB,
    symbol: str,
    duration: str,
    bar_size: str,
    whatToShow: str = "TRADES",
    useRTH: bool = False,
) :
    """
    Return a pandas.DataFrame of historical bars (index = date).
    Columns include: open, high, low, close, volume, etc.
    """
    contract = Stock(symbol, "SMART", "USD")
    bars = ib.reqHistoricalData(
        contract=contract,
        endDateTime="",
        durationStr=duration,
        barSizeSetting=bar_size,
        whatToShow=whatToShow,
        useRTH=useRTH,
        formatDate=2,
        keepUpToDate=False,
    )
    df = util.df(bars)
    if df is not None and not df.empty:
        if "date" in df.columns:
            df.set_index("date", inplace=True)
    return df
