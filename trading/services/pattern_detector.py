import pandas as pd
import numpy as np

class PatternDetector:
    def __init__(self):
        pass
    
    def detect_head_shoulders(self, df):
        if len(df) < 50:
            return False, 0
        highs = df['high'].values
        peaks = []
        for i in range(5, len(highs)-5):
            if highs[i] > highs[i-5:i].max() and highs[i] > highs[i+1:i+6].max():
                peaks.append((i, highs[i]))
        if len(peaks) >= 3:
            left = peaks[-3][1] if len(peaks) >= 3 else 0
            head = peaks[-2][1] if len(peaks) >= 2 else 0
            right = peaks[-1][1] if len(peaks) >= 1 else 0
            if head > left and head > right and abs(left - right) / head < 0.1:
                return True, 0.85
        return False, 0
    
    def detect_double_top(self, df):
        if len(df) < 30:
            return False, 0
        highs = df['high'].values[-30:]
        peaks = []
        for i in range(2, len(highs)-2):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                peaks.append(highs[i])
        if len(peaks) >= 2:
            if abs(peaks[-1] - peaks[-2]) / peaks[-2] < 0.02:
                return True, 0.8
        return False, 0
    
    def detect_double_bottom(self, df):
        if len(df) < 30:
            return False, 0
        lows = df['low'].values[-30:]
        bottoms = []
        for i in range(2, len(lows)-2):
            if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                bottoms.append(lows[i])
        if len(bottoms) >= 2:
            if abs(bottoms[-1] - bottoms[-2]) / bottoms[-2] < 0.02:
                return True, 0.8
        return False, 0
    
    def detect_pattern(self, df):
        patterns = []

        hs, conf_hs = self.detect_head_shoulders(df)
        if hs:
            patterns.append(("HEAD_SHOULDERS", conf_hs))

        dt, conf_dt = self.detect_double_top(df)
        if dt:
            patterns.append(("DOUBLE_TOP", conf_dt))

        db, conf_db = self.detect_double_bottom(df)
        if db:
            patterns.append(("DOUBLE_BOTTOM", conf_db))

        if not patterns:
            return {"pattern": "NONE", "confidence": 0}

    # pick best pattern
        best_pattern = max(patterns, key=lambda x: x[1])

        return {
            "pattern": best_pattern[0],
            "confidence": best_pattern[1]
        }

pattern_detector = PatternDetector()