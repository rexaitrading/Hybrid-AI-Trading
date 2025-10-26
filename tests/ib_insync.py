# test stub for ib_insync used by subprocessed runners
class _Dummy:
    def __init__(self,*a,**k): pass
    def __call__(self,*a,**k): return self
    def __getattr__(self,_): return self
class IB(_Dummy):
    def connect(self,*a,**k): return True
    def disconnect(self,*a,**k): return None
class Contract(_Dummy): pass
class Stock(_Dummy): pass
class Forex(_Dummy): pass
class MarketOrder(_Dummy): pass
class LimitOrder(_Dummy): pass
class ContractDetails(_Dummy): pass
class Ticker(_Dummy): pass
class util(_Dummy):
    @staticmethod
    def startLoop(*a,**k): pass
