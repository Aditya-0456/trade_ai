# run_pipeline.py

from services.upstox_api import fetch_market_data
from services.strategy_engine import StrategyEngine
from ml_model.lightgbm_model import LightGBMModel

ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI1RENHRFYiLCJqdGkiOiI2OWQ2OWM3ZmVmMTNhOTdjYzIxZjc4ZTkiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlhdCI6MTc3NTY3MjQ0NywiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxNzc1Njg1NjAwfQ.EDgAfAle-NOD8ANgFFplAEMalGi08PJzPRFwMMONdL4"
SYMBOL = "NSE|INE002A01018"


def run_pipeline():

    print("🚀 Starting Trading Pipeline...\n")

    # 1. FETCH DATA
    data = fetch_market_data(SYMBOL, ACCESS_TOKEN, days=60)

    if data is None or data.empty:
        print("❌ Data fetch failed")
        return

    print("✅ Data fetched:", len(data), "rows")

    # 2. ML MODEL
    model = LightGBMModel(SYMBOL)

    print("Training model...")
    result = model.train(data)

    if not result['success']:
        print("❌ Training failed:", result['error'])
        return

    print("✅ Model trained (accuracy:", result['accuracy'], ")")

    # 3. ML PREDICTION (probability)
    ml_prob = model.predict(data)

    print("🤖 ML Prediction (probability):", ml_prob)

    # 4. STRATEGY
    strategy = StrategyEngine(SYMBOL)
    signal_data = strategy.get_final_signal(data)

    print("\n📊 STRATEGY OUTPUT:")
    print(signal_data)

    # 5. FINAL DECISION (ML + Strategy combine)
    final_signal = "HOLD"

    if ml_prob > 0.6 and signal_data['signal'] == "BUY":
        final_signal = "BUY"

    elif ml_prob < 0.4 and signal_data['signal'] == "SELL":
        final_signal = "SELL"

    print("\n🔥 FINAL SIGNAL:", final_signal)
    print("Confidence:", signal_data['confidence'])


if __name__ == "__main__":
    run_pipeline()