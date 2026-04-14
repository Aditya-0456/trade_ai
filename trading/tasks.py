from celery import shared_task
from django.core.cache import cache
from datetime import datetime
import logging
from .models import TradingSession, Signal, NSEStock

logger = logging.getLogger(__name__)

@shared_task
def monitor_stop_losses():
    """Monitor and trigger stop losses"""
    from .models import Position, StopLossOrder, Trade
    from .services.upstox_api import UpstoxAPI
    from .services.order_executor import OrderExecutor
    
    positions = Position.objects.filter(stop_loss__isnull=False)
    
    for position in positions:
        try:
            session = TradingSession.objects.get(user=position.user, is_active=True)
            client = UpstoxAPI(session.access_token)
            quote = client.get_quote(position.symbol.symbol)
            
            if quote and quote['ltp'] <= position.stop_loss:
                executor = OrderExecutor(position.user, session.access_token)
                executor.close_position(position.symbol.symbol)
                logger.info(f"Stop loss triggered for {position.symbol.symbol}")
        except Exception as e:
            logger.error(f"Stop loss monitoring error: {e}")

@shared_task
def refresh_signals():
    """Auto refresh signals for all active users"""
    from .models import TradingSession, Signal, NSEStock
    from .services.strategy_engine import StrategyEngine
    from .services.upstox_api import UpstoxAPI
    import pandas as pd
    
    sessions = TradingSession.objects.filter(is_active=True)
    
    for session in sessions:
        try:
            client = UpstoxAPI(session.access_token)
            symbols = NSEStock.objects.filter(is_active=True)[:20]
            
            for stock in symbols:
                historical = client.get_historical(stock.symbol, days=100)
                if historical and len(historical) >= 50:
                    df = pd.DataFrame(historical)
                    engine = StrategyEngine(stock.symbol)
                    signal_result = engine.get_final_signal(df)
                    quote = client.get_quote(stock.symbol)
                    current_price = quote['ltp'] if quote else df['close'].iloc[-1]
                    
                    Signal.objects.create(
                        user=session.user,
                        symbol=stock,
                        signal=signal_result['signal'],
                        confidence=signal_result['confidence'],
                        price=current_price,
                        reason=signal_result.get('reason', '')
                    )
        except Exception as e:
            logger.error(f"Signal refresh error for user {session.user.id}: {e}")

@shared_task
def update_daily_performance():
    """Update daily performance records"""
    from .models import User, Trade, DailyPerformance
    from datetime import date
    from django.db.models import Sum
    
    for user in User.objects.all():
        today = date.today()
        trades = Trade.objects.filter(user=user, created_at__date=today)
        
        if trades.exists():
            total_pnl = trades.aggregate(total=Sum('pnl'))['total'] or 0
            winning_trades = trades.filter(pnl__gt=0).count()
            
            DailyPerformance.objects.update_or_create(
                user=user,
                date=today,
                defaults={
                    'starting_balance': 0,
                    'ending_balance': 0,
                    'pnl': total_pnl,
                    'pnl_percent': 0,
                    'trades_count': trades.count(),
                    'winning_trades': winning_trades,
                    'losing_trades': trades.count() - winning_trades,
                    'win_rate': (winning_trades / trades.count()) * 100 if trades.count() > 0 else 0
                }
            )

@shared_task
def cleanup_old_signals():
    """Delete old signals to save space"""
    from .models import Signal
    from datetime import timedelta
    from django.utils import timezone
    
    threshold = timezone.now() - timedelta(days=7)
    deleted = Signal.objects.filter(created_at__lt=threshold, executed=True).delete()
    logger.info(f"Cleaned up {deleted[0]} old signals")