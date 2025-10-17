from pathlib import Path
from datetime import datetime
import pandas as pd

class FeatureStore:
    def __init__(self, root="data/feature_store"):
        self.root = Path(root)
        (self.root / "quotes").mkdir(parents=True, exist_ok=True)

    def write_quote(self, symbol: str, ts: datetime, **fields):
        df = pd.DataFrame([{ "ts": ts, "symbol": symbol, **fields }])
        day = ts.strftime("%Y%m%d")
        pth = self.root / "quotes" / f"{symbol}_{day}.parquet"
        if pth.exists():
            old = pd.read_parquet(pth)
            df = pd.concat([old, df], ignore_index=True)
        df.to_parquet(pth, index=False)
