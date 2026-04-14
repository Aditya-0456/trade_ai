import pandas as pd
import numpy as np
from .pattern_detector import pattern_detector

class StrategyEngine:
    def __init__(self, symbol):
        self.symbol = symbol
    
    def calculate_technical_score(self, df):
        if len(df) < 50:
            return 0.5
        latest = df.iloc[-1]
        sma_10 = df['close'].rolling(10).mean().iloc[-1]
        sma_20 = df['close'].rolling(20).mean().iloc[-1]
        sma_50 = df['close'].rolling(50).mean().iloc[-1]
        buy_score, sell_score = 0, 0
        if sma_10 > sma_20 > sma_50:
            buy_score += 0.35
        elif sma_10 < sma_20 < sma_50:
            sell_score += 0.35
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        loss = loss.replace(0, 1e-10)       
        rs = gain / loss
        rsi = rsi.iloc[-1]
        if rsi < 30:
            buy_score += 0.3
        elif rsi > 70:
            sell_score += 0.3
        vol_ma = df['volume'].rolling(20).mean().iloc[-1]
        vol_ratio = df['volume'].iloc[-1] / vol_ma if vol_ma > 0 else 1
        if vol_ratio > 1.5 and latest['close'] > latest['open']:
            buy_score += 0.2
        elif vol_ratio > 1.5 and latest['close'] < latest['open']:
            sell_score += 0.2
        ema_12 = df['close'].ewm(span=12).mean()
        ema_26 = df['close'].ewm(span=26).mean()

        macd_line = ema_12 - ema_26
        macd_signal = macd_line.ewm(span=9).mean()

        if macd_line.iloc[-1] > macd_signal.iloc[-1]:
            buy_score += 0.15
        else:
            sell_score += 0.15
        total = buy_score + sell_score
        return buy_score / total if total > 0 else 0.5
    
    def get_final_signal(self, df):
        technical_score = self.calculate_technical_score(df)

        # 🔥 Pattern detection
        pattern_result = pattern_detector.detect_pattern(df)
        pattern = pattern_result["pattern"]
        pattern_conf = pattern_result["confidence"]

        # 🎯 Convert pattern to score
        pattern_score = 0.5

        if pattern == "DOUBLE_BOTTOM":
            pattern_score = 0.7
        elif pattern == "HEAD_SHOULDERS" or pattern == "DOUBLE_TOP":
            pattern_score = 0.3

        # 🔥 Combine both (VERY IMPORTANT)
        final_score = (technical_score * 0.7) + (pattern_score * 0.3)

        # 🚀 Final decision
        if final_score > 0.65:
            return {
                'signal': 'BUY',
                'confidence': min(final_score, 0.95),
                'reason': f'Technical + Pattern ({pattern})'
            }
        elif final_score < 0.35:
            return {
                'signal': 'SELL',
                'confidence': min(1 - final_score, 0.95),
                'reason': f'Technical + Pattern ({pattern})'
            }
        else:
            return {
                'signal': 'HOLD',
                'confidence': 0.5,
                'reason': 'Mixed signals'
            }