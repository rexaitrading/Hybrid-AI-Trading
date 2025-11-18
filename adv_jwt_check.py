import os
import time
import json
import uuid
from time import perf_counter

import requests
import jwt  # PyJWT

from hybrid_ai_trading.providers.qos import log_provider_qos


def build_rest_jwt(key_name: str, private_key: str, method: str, path: str) -> tuple[str, str]:
    """
    Build a Coinbase Advanced Trade REST JWT using ES256.

    key_name:    full "organizations/.../apiKeys/..." string
    private_key: full EC PRIVATE KEY PEM (multi-line)
    method:      HTTP method, e.g. "GET"
    path:        request path, e.g. "/api/v3/brokerage/accounts"
    """
    now = int(time.time())
    host = "api.coinbase.com"

    # Coinbase format: "GET api.coinbase.com/api/v3/brokerage/accounts"
    uri = f"{method.upper()} {host}{path}"

    payload: dict[str, object] = {
        "iss": "coinbase-cloud",
        "nbf": now,
        "exp": now + 120,
        "sub": key_name,
        "uri": uri,
    }

    headers = {
        "kid": key_name,
        "nonce": uuid.uuid4().hex,
    }

    token = jwt.encode(payload, private_key, algorithm="ES256", headers=headers)
    if isinstance(token, bytes):
        token = token.decode("utf-8")

    return token, uri


def main() -> None:
    key_name = os.environ.get("COINBASE_ADV_KEY_NAME")
    private_key = os.environ.get("COINBASE_ADV_PRIVATE_KEY")

    if not key_name or not private_key:
        raise SystemExit("COINBASE_ADV_KEY_NAME / COINBASE_ADV_PRIVATE_KEY not set")

    method = "GET"
    path = "/api/v3/brokerage/accounts"

    jwt_token, uri = build_rest_jwt(key_name, private_key, method, path)

    url = f"https://api.coinbase.com{path}"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json",
    }

    t0 = perf_counter()
    resp = requests.get(url, headers=headers, timeout=10)
    latency = perf_counter() - t0
    status = resp.status_code

    print("REQUEST URI:", uri)
    print("URL:        ", url)
    print("STATUS", status)

    try:
        body = resp.json()
        body_str = json.dumps(body, indent=2)
    except Exception:
        body = None
        body_str = resp.text

    if len(body_str) > 2000:
        body_str = body_str[:2000] + "... [truncated]"
    print("BODY", body_str)

    ok = status == 200
    extra = {"endpoint": path}

    log_provider_qos(
        "coinbase",
        ok=ok,
        latency_s=latency,
        status_code=status,
        extra=extra,
    )

    # Preserve existing behavior: non-zero exit on non-200
    if not ok:
        raise SystemExit(f"Non-200 from Coinbase: {status}")


if __name__ == "__main__":
    main()