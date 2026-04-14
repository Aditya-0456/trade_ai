from services.strategy_engine import StrategyEngine
from services.backtester import Backtester
from services.upstox_api import UpstoxAPI

# 🔥 API
api = UpstoxAPI(access_token="eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI1RENHRFYiLCJqdGkiOiI2OWNkNDk2ZTg5N2IzZDQ0NDlkMWMzZWIiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlhdCI6MTc3NTA2MTM1OCwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxNzc1MDgwODAwfQ.BxaV9eV7_oUwM0NoLShWF15y1Daamm6ES-ddVFCw81U")

# 🔥 Data
df = api.get_historical("RELIANCE", days=200)
if df is None or df.empty:
    print("No data received ❌")
else:
    print(df.head())

# 🚀 Strategy + Backtest
#strategy = StrategyEngine(symbol="RELIANCE")
#bt = Backtester(strategy)

#results = bt.run(df)

#print(results) # ⛔ stop execution here
#strategy = StrategyEngine(symbol="RELIANCE")

#bt = Backtester(strategy)

#results = bt.run(df)
#print(df.columns)

#print(results)