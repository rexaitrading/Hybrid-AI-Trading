from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Optional

from ib_insync import IB, util

from .structured_log import get_logger

logger = get_logger("hybrid_ai_trading.ib")

def _bool_env(name: str, default: str = "0") -> bool:
    return os.getenv(name, default) in ("1","true","True","YES","yes")

def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default

DEFAULT_HOST = os.getenv("IB_HOST", "127.0.0.1")
DEFAULT_PORT = _int_env("IB_PORT", 4002)
DEFAULT_TIMEOUT = _int_env("IB_TIMEOUT", 20)

def _attach_default_listeners(ib: IB) -> None:
    def onError(reqId, code, msg, contract):
        payload = {"ib_reqId": reqId, "ib_code": code, "ib_text": msg}
        try:
            if contract:
                payload["ib_contract"] = getattr(contract, "localSymbol", None) or getattr(contract, "conId", None)
        except Exception:
            pass
        logger.warning("ib_error | %s", payload)
    ib.errorEvent += onError
    ib.disconnectedEvent += (lambda: logger.warning("ib_disconnected"))
    ib.connectedEvent += (lambda: logger.info("ib_connected"))

def _resolve_use_ssl(explicit: Optional[bool]) -> bool:
    if explicit is not None:
        return bool(explicit)
    if "IB_SMOKE_SSL" in os.environ:
        return _bool_env("IB_SMOKE_SSL", "0")
    return _bool_env("IB_USE_SSL", "0")

def connect_ib(
    host: Optional[str] = None,
    port: Optional[int] = None,
    client_id: Optional[int] = None,
    timeout: Optional[int] = None,
    market_data_type: Optional[int] = 3,
    log: bool = False,
    use_ssl: Optional[bool] = None,
) -> IB:
    """
    Resilient IB connect:
      - Host/Port from env (defaults 127.0.0.1:4002)
      - UseSSL from explicit/IB_SMOKE_SSL/IB_USE_SSL (default False)
      - ClientId from env or defaults (930 for ssl=0, 931 for ssl=1)
      - Retries with clientId bump on:
          * code 326 "already in use"
          * "client id ... already in use"
          * "Peer closed connection"
          * TimeoutError
    """
    if log:
        util.logToConsole(True)

    h = host or DEFAULT_HOST
    p = int(port or DEFAULT_PORT)
    t = int(timeout or DEFAULT_TIMEOUT)
    ssl_flag = _resolve_use_ssl(use_ssl)

    cid_env = os.getenv("IB_CLIENT_ID")
    cid = int(cid_env) if cid_env is not None else (931 if ssl_flag else 930)
    if client_id is not None:
        cid = int(client_id)

    last_err: Optional[Exception] = None
    max_attempts = 6

    for attempt in range(max_attempts):
        ib = IB()
        try:
            ib.client.setConnectOptions(f"UseSSL={1 if ssl_flag else 0}")
            logger.info("ib_connect_start", extra={"host": h, "port": p, "clientId": cid, "attempt": attempt, "ssl": int(ssl_flag)})

            ok = ib.connect(h, p, clientId=cid, timeout=t)
            if not ok:
                raise RuntimeError("connect returned falsy")

            _attach_default_listeners(ib)

            if market_data_type is not None:
                try:
                    ib.reqMarketDataType(int(market_data_type))
                except Exception as e:
                    logger.warning("ib_req_mdt_failed | %s", {"error": str(e)})

            logger.info("ib_connect_ok", extra={"host": h, "port": p, "clientId": cid, "attempt": attempt, "ssl": int(ssl_flag)})
            return ib

        except Exception as e:
            last_err = e
            emsg = str(e)
            logger.warning("ib_connect_retry", extra={"attempt": attempt, "clientId": cid, "ssl": int(ssl_flag), "error": emsg[:400]})
            try:
                ib.disconnect()
            except Exception:
                pass

            # bump on the classic transient cases
            bump_reasons = (
                "already in use",
                "client id is already in use",
                "Peer closed connection",
                "TimeoutError",
            )
            if any(s.lower() in emsg.lower() for s in bump_reasons):
                cid += 1
                time.sleep(0.8 + 0.5 * attempt)
                continue

            # unknown hard failure: stop early
            raise

    logger.error("ib_connect_failed", extra={"error": str(last_err) if last_err else "unknown"})
    raise last_err if last_err else RuntimeError("IB connect failed")

@contextmanager
def ib_session(
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
    client_id: Optional[int] = None,
    timeout: Optional[int] = None,
    market_data_type: Optional[int] = 3,
    log: bool = False,
    use_ssl: Optional[bool] = None,
):
    ib = connect_ib(
        host=host,
        port=port,
        client_id=client_id,
        timeout=timeout,
        market_data_type=market_data_type,
        log=log,
        use_ssl=use_ssl,
    )
    try:
        yield ib
    finally:
        try:
            ib.disconnect()
            logger.info("ib_disconnect_ok")
        except Exception as e:
            logger.warning("ib_disconnect_err | %s", {"error": str(e)})
