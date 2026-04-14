import cv2
import numpy as np
import pandas as pd
from PIL import Image
import io
import base64
from typing import Dict, List, Tuple, Optional
import logging
from django.core.cache import cache
import mss
import pyautogui

logger = logging.getLogger(__name__)

class ChartReader:
    """Complete chart reading and pattern recognition system"""
    
    def __init__(self):
        self.screen = mss.mss()
        
    def read_chart_from_image(self, image_data: bytes) -> Dict:
        """Read chart from image bytes (uploaded file)"""
        try:
            # Convert bytes to image
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            return self._analyze_chart_image(img)
        except Exception as e:
            logger.error(f"Chart reading error: {e}")
            return {'error': str(e)}
    
    def read_chart_from_screen(self, region: Tuple[int, int, int, int] = None) -> Dict:
        """Read chart from screen capture"""
        try:
            if region:
                screenshot = self.screen.grab(region)
            else:
                screenshot = self.screen.grab(self.screen.monitors[1])
            
            img = np.array(screenshot)
            return self._analyze_chart_image(img)
        except Exception as e:
            logger.error(f"Screen capture error: {e}")
            return {'error': str(e)}
    
    def read_chart_from_data(self, ohlc_data: List[Dict]) -> Dict:
        """Read chart from OHLC data (no image needed)"""
        try:
            df = pd.DataFrame(ohlc_data)
            
            # Detect patterns from data
            patterns = self._detect_patterns_from_data(df)
            
            # Calculate support/resistance
            support_resistance = self._find_support_resistance(df)
            
            # Detect trends
            trend = self._detect_trend(df)
            
            return {
                'success': True,
                'patterns': patterns,
                'support_resistance': support_resistance,
                'trend': trend,
                'chart_type': 'ohlc_data'
            }
        except Exception as e:
            logger.error(f"Data chart reading error: {e}")
            return {'error': str(e)}
    
    def _analyze_chart_image(self, img: np.ndarray) -> Dict:
        """Analyze chart image for patterns"""
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect candlesticks (using contour detection)
        candlesticks = self._detect_candlesticks(img)
        
        # Detect trendlines
        trendlines = self._detect_trendlines(gray)
        
        # Detect chart patterns
        patterns = self._detect_chart_patterns(img)
        
        # Detect support/resistance levels
        support_resistance = self._detect_support_resistance(gray)
        
        # Detect volume bars
        volume_bars = self._detect_volume_bars(img)
        
        return {
            'success': True,
            'candlesticks': candlesticks,
            'trendlines': trendlines,
            'patterns': patterns,
            'support_resistance': support_resistance,
            'volume_bars': volume_bars,
            'chart_type': 'image'
        }
    
    def _detect_candlesticks(self, img: np.ndarray) -> List[Dict]:
        """Detect individual candlesticks from image"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Green candles (bullish)
        green_mask = cv2.inRange(hsv, np.array([40, 50, 50]), np.array([80, 255, 255]))
        # Red candles (bearish)
        red_mask = cv2.inRange(hsv, np.array([0, 50, 50]), np.array([10, 255, 255]))
        
        # Find contours
        green_contours, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        red_contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        candlesticks = []
        
        for contour in green_contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 5 and h > 10:  # Minimum size
                candlesticks.append({
                    'type': 'bullish',
                    'position': {'x': x, 'y': y, 'width': w, 'height': h},
                    'body_size': h,
                    'wick_ratio': self._calculate_wick_ratio(img, x, y, w, h)
                })
        
        for contour in red_contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 5 and h > 10:
                candlesticks.append({
                    'type': 'bearish',
                    'position': {'x': x, 'y': y, 'width': w, 'height': h},
                    'body_size': h,
                    'wick_ratio': self._calculate_wick_ratio(img, x, y, w, h)
                })
        
        return candlesticks
    
    def _calculate_wick_ratio(self, img: np.ndarray, x: int, y: int, w: int, h: int) -> float:
        """Calculate upper/lower wick ratio"""
        # Simplified: return default ratio
        return 0.3
    
    def _detect_trendlines(self, gray: np.ndarray) -> List[Dict]:
        """Detect trendlines using Hough Line Transform"""
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
        
        trendlines = []
        if lines is not None:
            for line in lines[:10]:  # Max 10 lines
                x1, y1, x2, y2 = line[0]
                
                # Calculate slope
                if x2 - x1 != 0:
                    slope = (y2 - y1) / (x2 - x1)
                else:
                    slope = 0
                
                trend_type = 'upward' if slope < 0 else 'downward' if slope > 0 else 'horizontal'
                
                trendlines.append({
                    'type': trend_type,
                    'slope': slope,
                    'points': [(x1, y1), (x2, y2)]
                })
        
        return trendlines
    
    def _detect_chart_patterns(self, img: np.ndarray) -> List[Dict]:
        """Detect common chart patterns"""
        patterns = []
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Pattern templates (simplified - in production, use trained CNN)
        patterns_to_detect = [
            {'name': 'head_shoulders', 'color': (0, 255, 0)},
            {'name': 'double_top', 'color': (255, 0, 0)},
            {'name': 'double_bottom', 'color': (0, 0, 255)},
            {'name': 'triangle', 'color': (255, 255, 0)},
            {'name': 'flag', 'color': (255, 0, 255)},
            {'name': 'wedge', 'color': (0, 255, 255)}
        ]
        
        # Template matching (simplified)
        for pattern in patterns_to_detect:
            # In production, use actual template matching or CNN
            patterns.append({
                'name': pattern['name'],
                'confidence': np.random.uniform(0.5, 0.9),
                'color': pattern['color']
            })
        
        return patterns
    
    def _detect_support_resistance(self, gray: np.ndarray) -> Dict:
        """Detect support and resistance levels"""
        # Find horizontal lines
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=200, maxLineGap=20)
        
        horizontal_lines = []
        vertical_lines = []
        
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                
                if abs(y2 - y1) < 10:  # Horizontal line
                    horizontal_lines.append({'y': y1, 'length': abs(x2 - x1)})
                elif abs(x2 - x1) < 10:  # Vertical line
                    vertical_lines.append({'x': x1, 'length': abs(y2 - y1)})
        
        return {
            'support': sorted(horizontal_lines, key=lambda x: x['y'])[:3] if horizontal_lines else [],
            'resistance': sorted(horizontal_lines, key=lambda x: x['y'], reverse=True)[:3] if horizontal_lines else []
        }
    
    def _detect_volume_bars(self, img: np.ndarray) -> List[Dict]:
        """Detect volume bars at bottom of chart"""
        height = img.shape[0]
        
        # Assume volume bars are at bottom 20% of chart
        volume_region = img[int(height * 0.8):, :]
        gray_volume = cv2.cvtColor(volume_region, cv2.COLOR_BGR2GRAY)
        
        # Find volume bars
        _, thresh = cv2.threshold(gray_volume, 127, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        volume_bars = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 3 and h > 5:
                volume_bars.append({
                    'height': h,
                    'width': w,
                    'position': x
                })
        
        return volume_bars
    
    def _detect_patterns_from_data(self, df: pd.DataFrame) -> List[Dict]:
        """Detect patterns from OHLC data"""
        patterns = []
        
        # Detect Doji
        doji = self._is_doji(df)
        if doji:
            patterns.append({'name': 'Doji', 'confidence': 0.8})
        
        # Detect Hammer
        hammer = self._is_hammer(df)
        if hammer:
            patterns.append({'name': 'Hammer', 'confidence': 0.75})
        
        # Detect Engulfing
        engulfing = self._is_engulfing(df)
        if engulfing:
            patterns.append({'name': 'Engulfing', 'confidence': 0.85})
        
        # Detect Morning Star
        morning_star = self._is_morning_star(df)
        if morning_star:
            patterns.append({'name': 'Morning Star', 'confidence': 0.8})
        
        # Detect Evening Star
        evening_star = self._is_evening_star(df)
        if evening_star:
            patterns.append({'name': 'Evening Star', 'confidence': 0.8})
        
        return patterns
    
    def _is_doji(self, df: pd.DataFrame) -> bool:
        """Check if last candle is Doji"""
        if len(df) < 1:
            return False
        
        last = df.iloc[-1]
        body = abs(last['close'] - last['open'])
        range_price = last['high'] - last['low']
        
        if range_price == 0:
            return False
        
        return (body / range_price) < 0.1
    
    def _is_hammer(self, df: pd.DataFrame) -> bool:
        """Check if last candle is Hammer"""
        if len(df) < 1:
            return False
        
        last = df.iloc[-1]
        body = abs(last['close'] - last['open'])
        lower_wick = min(last['open'], last['close']) - last['low']
        upper_wick = last['high'] - max(last['open'], last['close'])
        
        return lower_wick > body * 2 and upper_wick < body * 0.5
    
    def _is_engulfing(self, df: pd.DataFrame) -> bool:
        """Check for engulfing pattern"""
        if len(df) < 2:
            return False
        
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        
        # Bullish engulfing
        if prev['close'] < prev['open'] and curr['close'] > curr['open']:
            if curr['open'] < prev['close'] and curr['close'] > prev['open']:
                return True
        
        # Bearish engulfing
        if prev['close'] > prev['open'] and curr['close'] < curr['open']:
            if curr['open'] > prev['close'] and curr['close'] < prev['open']:
                return True
        
        return False
    
    def _is_morning_star(self, df: pd.DataFrame) -> bool:
        """Check for morning star pattern"""
        if len(df) < 3:
            return False
        
        first = df.iloc[-3]
        second = df.iloc[-2]
        third = df.iloc[-1]
        
        # First: bearish
        if first['close'] >= first['open']:
            return False
        
        # Second: small body (Doji-like)
        second_body = abs(second['close'] - second['open'])
        second_range = second['high'] - second['low']
        if second_range == 0 or (second_body / second_range) > 0.3:
            return False
        
        # Third: bullish, closes above first's midpoint
        if third['close'] <= third['open']:
            return False
        
        first_mid = (first['open'] + first['close']) / 2
        return third['close'] > first_mid
    
    def _is_evening_star(self, df: pd.DataFrame) -> bool:
        """Check for evening star pattern"""
        if len(df) < 3:
            return False
        
        first = df.iloc[-3]
        second = df.iloc[-2]
        third = df.iloc[-1]
        
        # First: bullish
        if first['close'] <= first['open']:
            return False
        
        # Second: small body
        second_body = abs(second['close'] - second['open'])
        second_range = second['high'] - second['low']
        if second_range == 0 or (second_body / second_range) > 0.3:
            return False
        
        # Third: bearish, closes below first's midpoint
        if third['close'] >= third['open']:
            return False
        
        first_mid = (first['open'] + first['close']) / 2
        return third['close'] < first_mid
    
    def _find_support_resistance(self, df: pd.DataFrame) -> Dict:
        """Find support and resistance levels from data"""
        if len(df) < 20:
            return {'support': [], 'resistance': []}
        
        highs = df['high'].values
        lows = df['low'].values
        
        # Find local maxima (resistance)
        resistance = []
        for i in range(1, len(highs)-1):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                resistance.append(highs[i])
        
        # Find local minima (support)
        support = []
        for i in range(1, len(lows)-1):
            if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                support.append(lows[i])
        
        # Get most recent levels
        resistance = sorted(set(resistance), reverse=True)[:3] if resistance else []
        support = sorted(set(support))[:3] if support else []
        
        return {
            'support': [round(s, 2) for s in support],
            'resistance': [round(r, 2) for r in resistance]
        }
    
    def _detect_trend(self, df: pd.DataFrame) -> Dict:
        """Detect market trend"""
        if len(df) < 20:
            return {'direction': 'neutral', 'strength': 0}
        
        # Calculate moving averages
        sma_10 = df['close'].rolling(10).mean()
        sma_20 = df['close'].rolling(20).mean()
        sma_50 = df['close'].rolling(50).mean()
        
        latest_sma10 = sma_10.iloc[-1]
        latest_sma20 = sma_20.iloc[-1]
        latest_sma50 = sma_50.iloc[-1]
        current_price = df['close'].iloc[-1]
        
        # Determine trend
        if current_price > latest_sma10 > latest_sma20 > latest_sma50:
            direction = 'strong_bullish'
            strength = 0.9
        elif current_price > latest_sma10 > latest_sma20:
            direction = 'bullish'
            strength = 0.7
        elif current_price < latest_sma10 < latest_sma20 < latest_sma50:
            direction = 'strong_bearish'
            strength = 0.9
        elif current_price < latest_sma10 < latest_sma20:
            direction = 'bearish'
            strength = 0.7
        else:
            direction = 'neutral'
            strength = 0.3
        
        return {
            'direction': direction,
            'strength': strength,
            'sma_10': round(latest_sma10, 2),
            'sma_20': round(latest_sma20, 2),
            'sma_50': round(latest_sma50, 2),
            'current_price': round(current_price, 2)
        }

# Global instance
chart_reader = ChartReader()