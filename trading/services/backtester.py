class Backtester:
    def __init__(self, strategy, initial_balance=100000):
        self.strategy = strategy
        self.balance = initial_balance
        self.position = 0
        self.trades = []

    def run(self, df):
        for i in range(50, len(df)):  # warmup for indicators
            data = df.iloc[:i]

            signal_data = self.strategy.get_final_signal(data)
            signal = signal_data['signal']
            price = data['close'].iloc[-1]

            if signal == 'BUY' and self.position == 0:
                self.position = self.balance / price
                self.entry_price = price
                self.balance = 0

            elif signal == 'SELL' and self.position > 0:
                self.balance = self.position * price
                pnl = (price - self.entry_price) * self.position

                self.trades.append(pnl)
                self.position = 0

        # final value
        final_value = self.balance + (self.position * df['close'].iloc[-1])

        return {
            "final_balance": final_value,
            "total_trades": len(self.trades),
            "total_pnl": sum(self.trades)
        }