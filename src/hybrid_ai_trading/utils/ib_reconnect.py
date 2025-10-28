from __future__ import annotations

import time
from typing import Any, Callable, Optional

try:
    from ib_insync import IB  # type: ignore
except Exception:
    IB = None  # type: ignore


def reconnect(
    ib: "IB",
    host: str = "127.0.0.1",
    port: int = 4002,
    client_id: Optional[int] = None,
    timeout: float = 30.0,
) -> "IB":
    """Idempotent reconnect using ib_insync.IB."""
    if ib is None:
        raise ValueError("ib instance is required")

    try:
        if getattr(ib, "isConnected", lambda: False)():
            return ib
    except Exception:
        pass

    try:
        ib.disconnect()
    except Exception:
        pass

    cid = client_id
    if cid is None:
        cid = getattr(ib, "clientId", 0) or 0

    ok = ib.connect(host, int(port), clientId=int(cid), timeout=float(timeout))
    if not ok and not getattr(ib, "isConnected", lambda: False)():
        raise RuntimeError(f"reconnect failed (host={host} port={port} clientId={cid})")
    return ib


def with_ib_reconnect(
    _func: Callable[..., Any] | None = None,
    *,
    retries: int = 1,
    backoff_sec: float = 1.0,
    host: str = "127.0.0.1",
    port: int = 4002,
    client_id: Optional[int] = None,
    timeout: float = 30.0,
) -> Callable[..., Any]:
    """
    Decorator usable as:
      @with_ib_reconnect
      @with_ib_reconnect(retries=2, backoff_sec=1.0, ...)
    Ensures an IB instance is connected; retries with exponential backoff.
    """

    def _decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        def _wrapper(*args: Any, **kwargs: Any) -> Any:
            _ib = kwargs.get("ib", None)
            if _ib is None:
                for a in args:
                    if hasattr(a, "connect") and hasattr(a, "isConnected"):
                        _ib = a
                        break
            if _ib is None:
                if IB is None:
                    raise RuntimeError("ib_insync.IB not available and no 'ib' instance provided")
                _ib = IB()

            # allow per-call overrides but default to decorator values
            h = kwargs.pop("host", host)
            p = int(kwargs.pop("port", port))
            cid = kwargs.pop("client_id", client_id)
            to = float(kwargs.pop("timeout", timeout))

            delay = float(backoff_sec)
            attempts = max(0, int(retries))
            for i in range(attempts + 1):
                try:
                    reconnect(_ib, host=h, port=p, client_id=cid, timeout=to)
                    kwargs["ib"] = _ib
                    return func(*args, **kwargs)
                except Exception:
                    if i >= attempts:
                        raise
                    time.sleep(delay)
                    delay = max(delay * 2.0, backoff_sec)

        _wrapper.__name__ = getattr(func, "__name__", "wrapped")
        _wrapper.__doc__ = getattr(func, "__doc__", None)
        return _wrapper

    if _func is not None and callable(_func):
        # bare form: @with_ib_reconnect
        return _decorate(_func)
    # parameterized form
    return _decorate
