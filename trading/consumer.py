import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MarketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.group_name = f"market_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        
        # Start sending updates
        await self.send_market_updates()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')
        
        if action == 'subscribe':
            symbol = data.get('symbol')
            if symbol:
                await self.send(text_data=json.dumps({
                    'type': 'subscribed',
                    'symbol': symbol
                }))
    
    async def send_market_updates(self):
        import asyncio
        while True:
            try:
                if self.user.is_authenticated:
                    symbols = await self.get_active_symbols()
                    quotes = {}
                    
                    for symbol in symbols[:10]:
                        quote = await self.get_quote_from_cache(symbol)
                        if quote:
                            quotes[symbol] = quote
                    
                    await self.send(text_data=json.dumps({
                        'type': 'market_update',
                        'data': quotes,
                        'timestamp': datetime.now().isoformat()
                    }))
                
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Market update error: {e}")
                await asyncio.sleep(5)
    
    @database_sync_to_async
    def get_active_symbols(self):
        from .models import NSEStock
        return list(NSEStock.objects.filter(is_active=True).values_list('symbol', flat=True)[:20])
    
    @database_sync_to_async
    def get_quote_from_cache(self, symbol):
        return cache.get(f"quote_{symbol}", None)

class SignalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.group_name = f"signals_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        
        if data.get('action') == 'get_signals':
            signals = await self.get_signals()
            await self.send(text_data=json.dumps({
                'type': 'signals',
                'data': signals
            }))
    
    @database_sync_to_async
    def get_signals(self):
        from .models import Signal
        signals = Signal.objects.filter(user=self.user, executed=False)[:20]
        return [{
            'id': s.id,
            'symbol': s.symbol.symbol,
            'signal': s.signal,
            'confidence': s.confidence,
            'price': s.price,
            'reason': s.reason
        } for s in signals]