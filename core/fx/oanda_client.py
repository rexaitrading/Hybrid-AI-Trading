import os
import requests
from dataclasses import dataclass
from typing import Dict, Any


class OandaConfigError(RuntimeError):
    """Raised when required OANDA env vars are missing."""
    pass


@dataclass
class FXQuote:
    instrument: str
    time: str
    bid: float
    ask: float

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    @property
    def spread(self) -> float:
        return self.ask - self.bid


class OandaFXClient:
    """
    Minimal OANDA v20 FX pricing client for HybridAITrading.

    Reads credentials from environment:
      - OANDA_API_HOST   (e.g. https://api-fxpractice.oanda.com)
      - OANDA_API_TOKEN  (personal access token)
      - OANDA_ACCOUNT_ID (e.g. 101-002-36136359-001)
    """

    def __init__(self) -> None:
        host = os.environ.get("OANDA_API_HOST")
        token = os.environ.get("OANDA_API_TOKEN")
        acct = os.environ.get("OANDA_ACCOUNT_ID")

        if not host or not token or not acct:
            missing = [
                name
                for name, value in [
                    ("OANDA_API_HOST", host),
                    ("OANDA_API_TOKEN", token),
                    ("OANDA_ACCOUNT_ID", acct),
                ]
                if not value
            ]
            raise OandaConfigError(f"Missing OANDA env vars: {', '.join(missing)}")

        self.host = host.rstrip("/")
        self.token = token
        self.account_id = acct

        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {self.token}"})

    def _get(self, path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        url = f"{self.host}{path}"
        resp = self._session.get(url, params=params or {}, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def price(self, instrument: str = "USD_CAD") -> FXQuote:
        """Return a single FXQuote for the given instrument (e.g. 'USD_CAD')."""
        data = self._get(
            f"/v3/accounts/{self.account_id}/pricing",
            params={"instruments": instrument},
        )

        prices = data.get("prices") or []
        if not prices:
            raise RuntimeError(f"No pricing returned for {instrument!r}")

        p = prices[0]
        bids = p.get("bids") or []
        asks = p.get("asks") or []

        if not bids or not asks:
            raise RuntimeError(f"Pricing object missing bid/ask for {instrument!r}")

        bid = float(bids[0]["price"])
        ask = float(asks[0]["price"])

        return FXQuote(
            instrument=instrument,
            time=p.get("time", ""),
            bid=bid,
            ask=ask,
        )