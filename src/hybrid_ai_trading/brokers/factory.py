from __future__ import annotations
import os
from typing import Literal
from .base import Broker

def make_broker() -> Broker:
    backend: Literal["fake","ib"] = os.getenv("BROKER_BACKEND","fake").lower()  # default to fake while IB is down
    if backend == "ib":
        from .ib_adapter import IBAdapter
        host = os.getenv("IB_HOST","127.0.0.1")
        port = int(os.getenv("IB_PORT","4002"))
        cid  = int(os.getenv("IB_CLIENT_ID","201"))
        tout = int(os.getenv("IB_TIMEOUT","15"))
        return IBAdapter(host=host, port=port, client_id=cid, timeout=tout)
    else:
        from tests.fakes.fake_ib import FakeIB  # local-only dependency
        return FakeIB()