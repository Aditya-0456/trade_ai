import time
from .upstox_api import UpstoxAPI
from ..models import Trade, Position, StopLossOrder, NSEStock
class OrderExecutor:
    def __init__(self, user, access_token):
        self.user = user
        self.client = UpstoxAPI(access_token)
    
    def execute_order(self, symbol, quantity, side, price, stop_loss=None, target=None):
        success, order_id, _ = self.client.place_order(symbol, quantity, side)
        if not success:
            return False, {'error': 'Order failed'}
        
        status = self._confirm_order(order_id, quantity)
        if not status:
            self.client.cancel_order(order_id)
            return False, {'error': 'Order confirmation failed'}
        
        stock = NSEStock.objects.get(symbol=symbol)
        trade = Trade.objects.create(
            user=self.user, symbol=stock, side=side, quantity=status['filled_quantity'],
            price=price, executed_price=status['average_price'], executed_quantity=status['filled_quantity'],
            order_id=order_id, status='EXECUTED'
        )
        
        if side == 'BUY':
            position, _ = Position.objects.update_or_create(
                user=self.user, symbol=stock,
                defaults={'quantity': status['filled_quantity'], 'avg_price': status['average_price'], 'stop_loss': stop_loss, 'target': target}
            )
            if stop_loss:
                sl_success, sl_order_id, _ = self.client.place_order(symbol, status['filled_quantity'], 'SELL', 'SL', trigger_price=stop_loss)
                if sl_success:
                    StopLossOrder.objects.create(trade=trade, symbol=stock, trigger_price=stop_loss, quantity=status['filled_quantity'], order_id=sl_order_id)
        else:
            position = Position.objects.filter(user=self.user, symbol=stock).first()
            if position:
                pnl = (status['average_price'] - position.avg_price) * status['filled_quantity']
                trade.pnl = pnl
                trade.pnl_percent = (pnl / (position.avg_price * status['filled_quantity'])) * 100 if position.avg_price > 0 else 0
                trade.save()
                new_quantity = position.quantity - status['filled_quantity']
                if new_quantity <= 0:
                    position.delete()
                else:
                    position.quantity = new_quantity
                    position.save()
        
        return True, {'order_id': order_id, 'quantity': status['filled_quantity'], 'price': status['average_price'], 'value': status['filled_quantity'] * status['average_price'], 'trade_id': trade.id}
    
    def _confirm_order(self, order_id, expected_quantity, max_attempts=5):
        for attempt in range(max_attempts):
            status = self.client.get_order_status(order_id)
            if status and status.get('status') == 'COMPLETE':
                return {'filled_quantity': status['filled_quantity'], 'average_price': status['average_price']}
            time.sleep(2 ** attempt)
        return None
    
    def close_position(self, symbol):
        from ..models import Position
        stock = NSEStock.objects.get(symbol=symbol)
        position = Position.objects.filter(user=self.user, symbol=stock).first()
        if not position:
            return False, {'error': 'Position not found'}
        return self.execute_order(symbol, position.quantity, 'SELL', position.current_price or position.avg_price)