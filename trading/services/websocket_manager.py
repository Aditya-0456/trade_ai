import websocket
import json
import threading
import time
import requests
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self, access_token):
        self.access_token = access_token
        self.ws = None
        self.is_connected = False
        self.subscribed_symbols = set()
        self.callbacks = []
        self.reconnect_count = 0
    
    def _get_ws_token(self):
        try:
            response = requests.get(
                "https://api.upstox.com/v2/feed/ws/token",
                headers={'Authorization': f'Bearer {self.access_token}'}
            )
            data = response.json()
            return data.get('data', {}).get('token')
        except Exception as e:
            logger.error(f"WebSocket token error: {e}")
            return None
    
    def connect(self):
        ws_token = self._get_ws_token()
        if not ws_token:
            return False
        
        ws_url = f"wss://api.upstox.com/v2/feed/ws/{ws_token}"
        self.ws = websocket.WebSocketApp(ws_url, on_open=self._on_open, on_message=self._on_message, on_error=self._on_error, on_close=self._on_close)
        wst = threading.Thread(target=self.ws.run_forever, kwargs={'ping_interval': 30, 'ping_timeout': 10})
        wst.daemon = True
        wst.start()
        return True
    
    def _on_open(self, ws):
        self.is_connected = True
        self.reconnect_count = 0
        logger.info("WebSocket connected")
        if self.subscribed_symbols:
            self._subscribe(list(self.subscribed_symbols))
    
    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            if 'symbol' in data and 'ltp' in data:
                cache.set(f"realtime_{data['symbol']}", {'ltp': float(data['ltp']), 'timestamp': time.time()}, timeout=2)
            for callback in self.callbacks:
                callback(data)
        except Exception as e:
            logger.error(f"WebSocket message error: {e}")
    
    def _on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")
        self.is_connected = False
        self._reconnect()
    
    def _on_close(self, ws, close_status_code, close_msg):
        logger.warning(f"WebSocket closed: {close_status_code}")
        self.is_connected = False
        self._reconnect()
    
    def _reconnect(self):
        if self.reconnect_count >= 5:
            return
        self.reconnect_count += 1
        delay = min(2 ** self.reconnect_count, 60)
        time.sleep(delay)
        self.connect()
    
    def _subscribe(self, symbols):
        if self.is_connected and self.ws:
            msg = {"type": "subscribe", "symbols": [f"NSE_EQ|{s}" for s in symbols]}
            self.ws.send(json.dumps(msg))
    
    def subscribe(self, symbols):
        self.subscribed_symbols.update(symbols)
        self._subscribe(symbols)
    
    def register_callback(self, callback):
        self.callbacks.append(callback)
    
    def get_realtime_price(self, symbol):
        data = cache.get(f"realtime_{symbol}")
        return data['ltp'] if data else 0