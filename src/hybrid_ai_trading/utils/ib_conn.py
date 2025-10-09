from __future__ import annotations
import os, time, logging
from contextlib import contextmanager
from typing import Optional
from ib_insync import IB, util
from .structured_log import get_logger
logger = get_logger("hybrid_ai_trading.ib")

DEFAULT_HOST = os.getenv("IB_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("IB_PORT", "4003"))
DEFAULT_CLIENT_ID = int(os.getenv("IB_CLIENT_ID", "3021"))
DEFAULT_TIMEOUT = int(os.getenv("IB_TIMEOUT", "60"))

def _attach_default_listeners(ib: IB):
    def onError(reqId, code, msg, contract):
        payload = {"reqId": reqId, "code": code, "msg": msg}
        try:
            if contract:
                payload["contract"] = getattr(contract, "localSymbol", None) or getattr(contract, "conId", None)
        except Exception:
            pass
        logger.warning("ib_error", extra=payload)
    ib.errorEvent += onError
    ib.disconnectedEvent += (lambda: logger.warning("ib_disconnected"))
    ib.connectedEvent    += (lambda: logger.info("ib_connected"))

def connect_ib(
    host: Optional[str] = None,
    port: Optional[int] = None,
    client_id: Optional[int] = None,
    timeout: Optional[int] = None,
    market_data_type: Optional[int] = 3,
    log: bool = False,
) -> IB:
    if log:
        util.logToConsole(True)
    h = host or DEFAULT_HOST
    p = int(port or DEFAULT_PORT)
    cid = int(client_id or DEFAULT_CLIENT_ID)
    t  = int(timeout or DEFAULT_TIMEOUT)

    last_err: Optional[Exception] = None
    for attempt in range(3):
        ib = IB()  # NEW IB per attempt
        try:
            logger.info("ib_connect_start", extra={"host": h, "port": p, "clientId": cid, "attempt": attempt})
            ok = ib.connect(h, p, clientId=cid, timeout=t)
            if not ok:
                raise RuntimeError("connect returned falsy")
            _attach_default_listeners(ib)
            if market_data_type is not None:
                ib.reqMarketDataType(int(market_data_type))
            logger.info("ib_connect_ok", extra={"host": h, "port": p, "clientId": cid, "attempt": attempt})
            return ib
        except Exception as e:
            last_err = e
            emsg = str(e)
            logger.warning("ib_connect_retry", extra={"attempt": attempt, "clientId": cid, "error": emsg[:400]})
            try:
                ib.disconnect()
            except Exception:
                pass
            if ("TimeoutError" in emsg) or ("refused" in emsg.lower()):
                cid += 1                # bump clientId to avoid stale session clash
                time.sleep(1.0 + attempt)
                continue
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
):
    ib = connect_ib(
        host=host, port=port, client_id=client_id,
        timeout=timeout, market_data_type=market_data_type, log=log
    )
    try:
        yield ib
    finally:
        try:
            ib.disconnect()
            logger.info("ib_disconnect_ok")
        except Exception as e:
            logger.warning("ib_disconnect_err", extra={"error": str(e)})