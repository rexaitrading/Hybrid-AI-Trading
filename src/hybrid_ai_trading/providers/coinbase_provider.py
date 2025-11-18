import os
import time
import uuid
import json
from typing import Any, Dict, Tuple

import jwt
import requests


class CoinbaseAuthError(RuntimeError):
    pass


class CoinbaseProvider:
    """
    Crypto backup provider for Hybrid AI Trading.

    - Uses Coinbase Advanced Trade REST API via CDP key (JWT/ES256)
    - Primary use: backup quotes / balances, CAD rails, failover from Kraken
    """

    HOST = "api.coinbase.com"

    def __init__(
        self,
        key_name: str | None = None,
        private_key: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.key_name = key_name or os.environ.get("COINBASE_ADV_KEY_NAME")
        self.private_key = private_key or os.environ.get("COINBASE_ADV_PRIVATE_KEY")
        self.timeout = timeout

        if not self.key_name or not self.private_key:
            raise CoinbaseAuthError(
                "COINBASE_ADV_KEY_NAME / COINBASE_ADV_PRIVATE_KEY not set"
            )

    # ---------- low-level JWT ----------

    def _build_rest_jwt(self, method: str, path: str) -> Tuple[str, str]:
        now = int(time.time())
        uri = f"{method.upper()} {self.HOST}{path}"

        payload: Dict[str, Any] = {
            "iss": "coinbase-cloud",
            "nbf": now,
            "exp": now + 120,
            "sub": self.key_name,
            "uri": uri,
        }
        headers = {
            "kid": self.key_name,
            "nonce": uuid.uuid4().hex,
        }

        token = jwt.encode(payload, self.private_key, algorithm="ES256", headers=headers)
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        return token, uri

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        token, uri = self._build_rest_jwt(method, path)
        url = f"https://{self.HOST}{path}"
        headers = kwargs.pop("headers", {}) or {}
        headers.setdefault("Authorization", f"Bearer {token}")
        headers.setdefault("Content-Type", "application/json")

        resp = requests.request(
            method=method,
            url=url,
            headers=headers,
            timeout=self.timeout,
            **kwargs,
        )
        return resp

    # ---------- public methods ----------

    def get_accounts(self) -> Dict[str, Any]:
        """Return Advanced Trade accounts payload."""
        path = "/api/v3/brokerage/accounts"
        resp = self._request("GET", path)
        try:
            data = resp.json()
        except Exception:
            raise CoinbaseAuthError(f"Non-JSON response: {resp.status_code} {resp.text[:200]}")

        if resp.status_code != 200:
            raise CoinbaseAuthError(
                f"Coinbase error {resp.status_code}: "
                f"{json.dumps(data)[:200]}"
            )
        return data

    def get_account_summary(self) -> Dict[str, Any]:
        """
        Convenience: returns a slim dict of account name -> balance.
        """
        data = self.get_accounts()
        out: Dict[str, Any] = {}
        for acct in data.get("accounts", []):
            name = acct.get("name")
            bal = acct.get("available_balance", {}) or {}
            out[name] = {
                "currency": bal.get("currency"),
                "value": float(bal.get("value") or 0.0),
                "type": acct.get("type"),
                "platform": acct.get("platform"),
            }
        return out