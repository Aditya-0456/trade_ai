import requests
import time
from datetime import datetime, timedelta
from django.core.cache import cache
import logging
import pandas as pd

logger = logging.getLogger(__name__)

class UpstoxAPI:
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = "https://api.upstox.com/v2"
        self.headers = {'Accept': 'application/json', 'Authorization': f'Bearer {access_token}'}
        self.last_call = 0
        self.min_interval = 0.6
    
    def _call(self, method, endpoint, data=None, params=None):
        now = time.time()
        if now - self.last_call < self.min_interval:
            time.sleep(self.min_interval - (now - self.last_call))
        self.last_call = time.time()
        
        url = f"{self.base_url}{endpoint}"
        try:
            if method == 'GET':
                r = requests.get(url, headers=self.headers, params=params, timeout=10)
            else:
                r = requests.post(url, headers=self.headers, json=data, timeout=10)
            print("URL:",r.url)
            print("RESPONSE:", r.text)
            if r.status_code == 200:
                return r.json()
            else:
                logger.error(f"API error {r.status_code}: {r.text[:200]}")
                return {'error': r.text[:200]}
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {'error': str(e)}
    
    def verify(self):
        result = self._call('GET', '/user/profile')
        if 'error' not in result and result.get('status') == 'success':
            return True, result.get('data', {})
        return False, {'error': result.get('error', 'Invalid token')}
    
    def get_balance(self):
        result = self._call('GET', '/user/get-funds-and-margin')
        if 'error' not in result:
            equity = result.get('data', {}).get('equity', {})
            return {'available': float(equity.get('available_balance', 0))}
        return {'available': 0}
    
    def get_historical(self, symbol, days=30):
        end = datetime.now() - timedelta(days=1)
        start = end - timedelta(days=days)

        instrument_key = f'NSE_EQ|{symbol}'

        endpoint = f"/historical-candle/{instrument_key}/day/{end.strftime('%Y-%m-%d')}/{start.strftime('%Y-%m-%d')}"
        #print("FINAL ENDPOINT:", endpoint)

        result = self._call('GET', endpoint)
        #print("RAW RESPONSE:", result)
        if 'error' not in result:
            candles = result.get('data', {}).get('candles', [])

            #if not candles:
                #return None

            df = pd.DataFrame(candles, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'io'
            ])

            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            #df.set_index('timestamp', inplace=True)

            return df

        
        return None
    
    def get_quote(self, symbol):
        cache_key = f"quote_{symbol}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        result = self._call('GET', '/market-quote/quotes', params={'symbol': f'NSE_EQ|{symbol}'})
        if 'error' not in result:
            data = result.get('data', [{}])[0]
            if data:
                quote = {
                    'symbol': symbol,
                    'ltp': float(data.get('last_price', 0)),
                    'open': float(data.get('open_price', 0)),
                    'high': float(data.get('high_price', 0)),
                    'low': float(data.get('low_price', 0)),
                    'volume': float(data.get('volume', 0))
                }
                cache.set(cache_key, quote, timeout=3)
                return quote
        return None
    
    def place_order(self, symbol, quantity, side):
        order_data = {
            'duration': 'DAY',
            'exchange': 'NSE_EQ',
            'instrument_token': f'NSE_EQ|{symbol}',
            'order_type': 'MARKET',
            'product': 'DELIVERY',
            'quantity': quantity,
            'transaction_type': side.upper(),
            'variety': 'NORMAL'
        }
        result = self._call('POST', '/order/place', data=order_data)
        if 'error' not in result and result.get('status') == 'success':
            return True, result.get('data', {}).get('order_id', ''), result.get('data', {})
        return False, '', {'error': result.get('message', 'Order failed')}
    
    def get_order_status(self, order_id):
        result = self._call('GET', '/order/details', params={'order_id': order_id})
        if 'error' not in result and result.get('status') == 'success':
            data = result.get('data', {})
            return {
                'status': data.get('status'),
                'filled_quantity': int(data.get('filled_quantity', 0)),
                'average_price': float(data.get('average_price', 0))
            }
        return None
    
    # ADD THIS AT BOTTOM

def fetch_market_data(symbol, access_token, days=30):

    api = UpstoxAPI(access_token)

    df = api.get_historical(symbol, days=days)

    if df is None or df.empty:
        print("❌ No data fetched from Upstox")
        return None

    # Rename columns for consistency
    df.rename(columns={
        'timestamp': 'date'
    }, inplace=True)

    # Add returns (VERY IMPORTANT for ML)
    df['returns'] = df['close'].pct_change()

    return df