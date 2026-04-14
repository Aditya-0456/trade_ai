from datetime import datetime, time
from django.core.cache import cache

class RiskManager:
    def __init__(self, user_id, balance):
        self.user_id = user_id
        self.balance = balance
        today = datetime.now().date()
        self.daily_pnl = cache.get(f"daily_pnl_{user_id}_{datetime.now().date()}", 0)
        self.trades_today = cache.get(f"trades_today_{user_id}_{datetime.now().date()}", 0)
        self.consecutive_losses = cache.get(f"consecutive_losses_{user_id}_{today}", 0)
    
    def can_trade(self):
        errors = []
        if self.balance < 5000:
            errors.append(f"Insufficient balance: ₹{self.balance}")
        daily_loss_limit = self.balance * 0.05
        if self.daily_pnl < -daily_loss_limit:
            errors.append(f"Daily loss limit reached: ₹{self.daily_pnl}")
        if self.trades_today >= 20:
            errors.append(f"Daily trade limit reached: {self.trades_today}")
        if self.consecutive_losses >= 3:
            errors.append(f"Consecutive losses: {self.consecutive_losses}")
            return False, errors
        now = datetime.now()
        if now.weekday() in [5, 6]:
            errors.append("Weekend")
        market_start = time(9, 15)
        market_end = time(15, 30)

        current_time = now.time()

        if current_time < market_start or current_time > market_end:
            errors.append("Market closed")
        return len(errors) == 0, errors
    
    def calculate_position_size(self, price, confidence, volatility=0.02):
        risk_per_trade = self.balance * 0.01 * confidence  # safer

        stop_loss_distance = price * volatility  # dynamic risk

        if stop_loss_distance == 0:
            return 1

        quantity = int(risk_per_trade / stop_loss_distance)

        max_qty = int(self.balance * 0.3 / price)
        quantity = min(quantity, max_qty)

        return max(quantity, 1)
    
    def calculate_stop_loss(self, entry_price, side):
        if side == 'BUY':
            return entry_price * 0.98
        return entry_price * 1.02
    
    def calculate_target(self, entry_price, side):
        if side == 'BUY':
            return entry_price * 1.04
        return entry_price * 0.96
    
    def update_trade_result(self, pnl):
        self.daily_pnl += pnl
        self.trades_today += 1
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        today = datetime.now().date()
        cache.set(f"daily_pnl_{self.user_id}_{today}", self.daily_pnl, 86400)
        cache.set(f"trades_today_{self.user_id}_{today}", self.trades_today, 86400)
        cache.set(f"consecutive_losses_{self.user_id}_{today}", self.consecutive_losses, 86400)