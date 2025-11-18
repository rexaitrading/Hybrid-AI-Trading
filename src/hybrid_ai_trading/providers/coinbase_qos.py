from time import perf_counter
from typing import Any, Dict

from .coinbase_provider import CoinbaseProvider, CoinbaseAuthError
from .qos import log_provider_qos


def probe_coinbase_accounts_with_qos() -> Dict[str, Any]:
    """
    Low-level QoS-aware probe of Coinbase Advanced Trade /accounts endpoint.

    Returns the JSON payload on success, and always logs a QoS entry.
    Raises CoinbaseAuthError on failure.
    """
    provider = CoinbaseProvider()
    path = "/api/v3/brokerage/accounts"

    t0 = perf_counter()
    resp = provider._request("GET", path)  # type: ignore[attr-defined]
    latency = perf_counter() - t0

    status = resp.status_code
    ok = status == 200

    try:
        data = resp.json()
    except Exception:
        data = None

    extra = {
        "endpoint": path,
    }

    log_provider_qos(
        "coinbase",
        ok=ok,
        latency_s=latency,
        status_code=status,
        extra=extra,
    )

    if not ok:
        # Reuse the provider's error type for callers
        snippet = ""
        if isinstance(data, dict):
            snippet = str(data)[:200]
        else:
            snippet = (resp.text or "")[:200]
        raise CoinbaseAuthError(f"Coinbase error {status}: {snippet}")

    # If data is None, surface that as an error
    if data is None:
        raise CoinbaseAuthError("Coinbase returned non-JSON or empty response")

    return data