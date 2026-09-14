"""Trading module stub — V2 da olib tashlangan."""
class _Stub:
    def __getattr__(self, name):
        def noop(*a, **k):
            return None
        return noop

_s = _Stub()

def get_current_price(): return {"price": 1000, "change_pct": 0}
def get_trading_stats(): return {"total_trades":0, "total_volume":0}
def get_user_open_position(uid): return None
def get_user_history(uid, limit=20): return []
def get_price_history(limit=300): return []
def get_ohlc_history(limit=80): return []
def tick_price(): return {"price": 1000}
def open_position(uid, d, a, dur): return False, "Trading V2 da o'chirilgan", None
