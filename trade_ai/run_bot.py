import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trade_ai.settings')  # 👈 change
django.setup()


from trading.services.upstox_api import UpstoxAPI
from trading.services.ml_services import train_model, load_model, predict_signal
import time

# ================================
# ⚙️ CONFIG
# ================================
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI1RENHRFYiLCJqdGkiOiI2OWRkZjhmYTU5ODYwMTEyNjRiMjhmMjEiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlhdCI6MTc3NjE1NDg3NCwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxNzc2MjA0MDAwfQ.lUm6M24DNrEOXxVfj5XCxnhIWtV_Lr0-95Cg7bH_-WE"
SYMBOL = "INE839G01010"   # stock
QUANTITY = 1              # safe start

# ================================
# 🚀 INIT API
# ================================
api = UpstoxAPI(access_token=ACCESS_TOKEN)

# ================================
# 🔐 VERIFY TOKEN
# ================================
status, user = api.verify()
if not status:
    print("❌ Invalid Token")
    exit()

print("✅ Logged in:", user)

# ================================
# 📊 FETCH DATA
# ================================
data = api.get_historical(SYMBOL, days=200)

if data is None or data.empty:
    print("❌ No data fetched")
    exit()

# ================================
# 🧠 MODEL LOAD / TRAIN
# ================================
try:
    model = load_model()
    print("✅ Model loaded")
except:
    print("🔥 Training model...")
    model = train_model(data)

# ================================
# 🤖 TRADING LOOP
# ================================
while True:
    try:
        print("\n🔄 Checking market...")

        # 📊 Latest data
        data = api.get_historical(SYMBOL, days=200)

        if data is None or data.empty:
            print("⚠️ Data issue")
            time.sleep(60)
            continue

        # 📈 Add returns (important)
        data['returns'] = data['close'].pct_change()
        data.dropna(inplace=True)

        # 🧠 Prediction
        signal = predict_signal(model, data)
        print("📊 Signal:", signal)

        # 💰 Live price
        quote = api.get_quote(SYMBOL)
        print("💲 LTP:", quote)

        # ============================
        # 🟢 BUY LOGIC
        # ============================
        if signal == "BUY":
            print("🟢 Placing BUY order...")
            success, order_id, _ = api.place_order(SYMBOL, QUANTITY, "BUY")
            print("Order:", success, order_id)

        # ============================
        # 🔴 SELL LOGIC
        # ============================
        elif signal == "SELL":
            print("🔴 Placing SELL order...")
            success, order_id, _ = api.place_order(SYMBOL, QUANTITY, "SELL")
            print("Order:", success, order_id)

        else:
            print("⚪ HOLD")

        # ⏱️ Wait
        time.sleep(60)

    except Exception as e:
        print("❌ Error:", e)
        time.sleep(60)