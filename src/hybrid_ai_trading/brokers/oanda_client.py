from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass
class OandaConfig:
    api_token: str
    account_id: str
    env: str = "practice"  # "practice" or "live"

    @property
    def base_url(self) -> str:
        if self.env == "live":
            return "https://api-fxtrade.oanda.com/v3"
        return "https://api-fxpractice.oanda.com/v3"

    @classmethod
    def from_env(cls) -> "OandaConfig":
        token = os.environ.get("OANDA_API_TOKEN") or ""
        account = os.environ.get("OANDA_ACCOUNT_ID") or ""
        env = os.environ.get("OANDA_ENV", "practice")
        if not token or not account:
            raise RuntimeError("OANDA_API_TOKEN or OANDA_ACCOUNT_ID missing in environment.")
        return cls(api_token=token, account_id=account, env=env)


class OandaClient:
    def __init__(self, config: OandaConfig) -> None:
        self._cfg = config
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {config.api_token}",
                "Content-Type": "application/json",
            }
        )

    def _url(self, path: str) -> str:
        return f"{self._cfg.base_url}{path}"

    def get_pricing(self, instruments: str) -> Dict[str, Any]:
        """
        instruments: comma-separated (e.g. 'EUR_USD,USD_CAD')
        """
        url = self._url(f"/accounts/{self._cfg.account_id}/pricing")
        resp = self._session.get(url, params={"instruments": instruments}, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def get_positions(self) -> Dict[str, Any]:
        url = self._url(f"/accounts/{self._cfg.account_id}/positions")
        resp = self._session.get(url, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def place_market_order(
        self,
        instrument: str,
        units: int,
        tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        units: positive for buy, negative for sell
        """
        url = self._url(f"/accounts/{self._cfg.account_id}/orders")
        body: Dict[str, Any] = {
            "order": {
                "instrument": instrument,
                "units": str(units),
                "type": "MARKET",
                "timeInForce": "FOK",
                "positionFill": "DEFAULT",
            }
        }
        if tag:
            body["order"]["clientExtensions"] = {"tag": tag}

        resp = self._session.post(url, json=body, timeout=5)
        resp.raise_for_status()
        return resp.json()