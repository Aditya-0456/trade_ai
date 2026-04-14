from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Avg, Count
import json
import pandas as pd
from datetime import datetime, timedelta

from .services.upstox_api import UpstoxAPI
from .services.strategy_engine import StrategyEngine
from .services.risk_manager import RiskManager
from .services.order_executor import OrderExecutor
from .services.chart_reader import chart_reader
from .ml_model.cnn_model import cnn_model
from .models import TradingSession, Trade, Position, Signal, NSEStock, Notification, DailyPerformance

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
    return render(request, 'trading/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    has_session = TradingSession.objects.filter(user=request.user, is_active=True).exists()
    symbols = list(NSEStock.objects.filter(is_active=True).values_list('symbol', flat=True)[:20])
    if not symbols:
        symbols = ['RELIANCE', 'HDFC', 'HDFCBANK', 'INFY', 'ICICIBANK', 'SBIN', 'TATAMOTORS', 'WIPRO']
    return render(request, 'trading/dashboard.html', {'has_session': has_session, 'symbols': symbols})

@login_required
def charts_page(request):
    return render(request, 'trading/charts.html')

@login_required
@csrf_exempt
def connect_upstox(request):
    data = json.loads(request.body)
    access_token = data.get('access_token', '').strip()
    if not access_token:
        return JsonResponse({'success': False, 'error': 'Access token required'})
    
    client = UpstoxAPI(access_token)
    success, result = client.verify()
    if not success:
        return JsonResponse({'success': False, 'error': result.get('error', 'Invalid token')})
    
    TradingSession.objects.filter(user=request.user).update(is_active=False)
    TradingSession.objects.create(
        user=request.user,
        access_token=access_token,
        user_id=result.get('user_id', ''),
        is_active=True
    )
    
    balance = client.get_balance()
    return JsonResponse({'success': True, 'message': 'Connected', 'balance': balance.get('available', 0)})

@login_required
def disconnect_upstox(request):
    TradingSession.objects.filter(user=request.user).update(is_active=False)
    return JsonResponse({'success': True})

@login_required
def get_signals(request):
    try:
        session = TradingSession.objects.get(user=request.user, is_active=True)
    except TradingSession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not connected'})
    
    client = UpstoxAPI(session.access_token)
    symbols = list(NSEStock.objects.filter(is_active=True).values_list('symbol', flat=True)[:20])
    if not symbols:
        symbols = ['RELIANCE', 'HDFC', 'HDFCBANK', 'INFY', 'ICICIBANK', 'SBIN', 'TATAMOTORS', 'WIPRO']
    
    signals = []
    for symbol in symbols:
        historical = client.get_historical(symbol, days=100)
        if historical and len(historical) >= 50:
            df = pd.DataFrame(historical)
            engine = StrategyEngine(symbol)
            signal_result = engine.get_final_signal(df)
            quote = client.get_quote(symbol)
            current_price = quote['ltp'] if quote else df['close'].iloc[-1]
            
            signal = Signal.objects.create(
                user=request.user,
                symbol=NSEStock.objects.get_or_create(symbol=symbol)[0],
                signal=signal_result['signal'],
                confidence=signal_result['confidence'],
                price=current_price,
                reason=signal_result.get('reason', '')
            )
            
            signals.append({
                'id': signal.id,
                'symbol': symbol,
                'signal': signal_result['signal'],
                'confidence': round(signal_result['confidence'], 3),
                'price': current_price,
                'reason': signal_result.get('reason', '')
            })
    
    return JsonResponse({'success': True, 'signals': signals})

@login_required
@csrf_exempt
def execute_trade(request):
    data = json.loads(request.body)
    symbol = data.get('symbol')
    signal_side = data.get('signal')
    confidence = float(data.get('confidence', 0.5))
    signal_id = data.get('signal_id')
    
    try:
        session = TradingSession.objects.get(user=request.user, is_active=True)
    except TradingSession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not connected'})
    
    stock, _ = NSEStock.objects.get_or_create(symbol=symbol)
    client = UpstoxAPI(session.access_token)
    quote = client.get_quote(symbol)
    if not quote or quote['ltp'] == 0:
        return JsonResponse({'success': False, 'error': 'Could not get price'})
    
    price = quote['ltp']
    balance = client.get_balance().get('available', 0)
    risk_manager = RiskManager(request.user.id, balance)
    can_trade, errors = risk_manager.can_trade()
    
    if not can_trade:
        return JsonResponse({'success': False, 'error': ' | '.join(errors)})
    
    existing_position = Position.objects.filter(user=request.user, symbol=stock).first()
    
    if signal_side == 'BUY' and existing_position:
        return JsonResponse({'success': False, 'error': f'Already have position in {symbol}'})
    
    if signal_side == 'SELL' and not existing_position:
        return JsonResponse({'success': False, 'error': f'No position to sell in {symbol}'})
    
    if signal_side == 'BUY':
        quantity = risk_manager.calculate_position_size(price, confidence, 0.02)
    else:
        quantity = existing_position.quantity
    
    if quantity == 0:
        return JsonResponse({'success': False, 'error': 'Position size too small'})
    
    executor = OrderExecutor(request.user, session.access_token)
    stop_loss = risk_manager.calculate_stop_loss(price, signal_side)
    target = risk_manager.calculate_target(price, signal_side)
    
    success, result = executor.execute_order(symbol, quantity, signal_side, price, stop_loss, target)
    
    if success:
        if signal_id:
            Signal.objects.filter(id=signal_id).update(executed=True)
        
        Notification.objects.create(
            user=request.user,
            type='trade',
            title=f'{signal_side} Order Executed',
            message=f'{quantity} shares of {symbol} at ₹{price}'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'{signal_side} order executed for {quantity} shares at ₹{price}',
            'order_id': result['order_id'],
            'quantity': result['quantity'],
            'price': result['price'],
            'value': result['value'],
            'stop_loss': stop_loss,
            'target': target
        })
    return JsonResponse({'success': False, 'error': result.get('error', 'Order failed')})

@login_required
def get_positions(request):
    positions = Position.objects.filter(user=request.user).select_related('symbol')
    
    try:
        session = TradingSession.objects.get(user=request.user, is_active=True)
        client = UpstoxAPI(session.access_token)
        for pos in positions:
            quote = client.get_quote(pos.symbol.symbol)
            if quote:
                pos.current_price = quote['ltp']
                pos.unrealized_pnl = (quote['ltp'] - pos.avg_price) * pos.quantity
                pos.save()
    except:
        pass
    
    position_data = []
    total_pnl = 0
    total_invested = 0
    
    for pos in positions:
        pnl = (pos.current_price - pos.avg_price) * pos.quantity if pos.current_price else 0
        total_pnl += pnl
        total_invested += pos.avg_price * pos.quantity
        
        position_data.append({
            'symbol': pos.symbol.symbol,
            'quantity': pos.quantity,
            'avg_price': round(pos.avg_price, 2),
            'current_price': round(pos.current_price, 2),
            'pnl': round(pnl, 2),
            'pnl_percent': round((pnl / (pos.avg_price * pos.quantity)) * 100, 2) if pos.avg_price > 0 else 0,
            'stop_loss': round(pos.stop_loss, 2) if pos.stop_loss else None,
            'target': round(pos.target, 2) if pos.target else None
        })
    
    return JsonResponse({
        'success': True,
        'positions': position_data,
        'total_pnl': round(total_pnl, 2),
        'total_invested': round(total_invested, 2),
        'return_percent': round((total_pnl / total_invested) * 100, 2) if total_invested > 0 else 0
    })

@login_required
def get_trades(request):
    trades = Trade.objects.filter(user=request.user).select_related('symbol').order_by('-created_at')[:50]
    trade_data = [{
        'id': t.id,
        'symbol': t.symbol.symbol,
        'side': t.side,
        'quantity': t.quantity,
        'price': round(t.price, 2),
        'value': round(t.quantity * t.price, 2),
        'pnl': round(t.pnl, 2),
        'pnl_percent': round(t.pnl_percent, 2),
        'time': t.created_at.strftime('%Y-%m-%d %H:%M:%S')
    } for t in trades]
    return JsonResponse({'success': True, 'trades': trade_data})

@login_required
def get_balance(request):
    try:
        session = TradingSession.objects.get(user=request.user, is_active=True)
        client = UpstoxAPI(session.access_token)
        balance_info = client.get_balance()
        balance = balance_info.get('available', 0)
    except:
        balance = 0
    
    positions = Position.objects.filter(user=request.user)
    unrealized_pnl = sum((p.current_price - p.avg_price) * p.quantity for p in positions if p.current_price)
    
    today = datetime.now().date()
    today_trades = Trade.objects.filter(user=request.user, created_at__date=today)
    today_pnl = today_trades.aggregate(total=Sum('pnl'))['total'] or 0
    
    return JsonResponse({
        'success': True,
        'balance': balance,
        'unrealized_pnl': round(unrealized_pnl, 2),
        'today_pnl': round(today_pnl, 2),
        'total_value': balance + unrealized_pnl
    })

@login_required
@csrf_exempt
def close_position(request):
    data = json.loads(request.body)
    symbol = data.get('symbol')
    
    try:
        stock = NSEStock.objects.get(symbol=symbol)
        position = Position.objects.get(user=request.user, symbol=stock)
    except:
        return JsonResponse({'success': False, 'error': 'Position not found'})
    
    try:
        session = TradingSession.objects.get(user=request.user, is_active=True)
    except:
        return JsonResponse({'success': False, 'error': 'Not connected'})
    
    executor = OrderExecutor(request.user, session.access_token)
    success, result = executor.close_position(symbol)
    
    if success:
        Notification.objects.create(
            user=request.user,
            type='trade',
            title='Position Closed',
            message=f'Closed {position.quantity} shares of {symbol}'
        )
        return JsonResponse({'success': True, 'message': f'Closed position for {symbol}'})
    return JsonResponse({'success': False, 'error': result.get('error', 'Failed to close')})

@login_required
@csrf_exempt
def upload_chart(request):
    if request.method == 'POST' and request.FILES.get('chart_image'):
        chart_image = request.FILES['chart_image']
        image_data = chart_image.read()
        result = chart_reader.read_chart_from_image(image_data)
        cnn_result = cnn_model.predict_pattern(image_data)
        return JsonResponse({'success': True, 'computer_vision': result, 'cnn_pattern': cnn_result})
    return JsonResponse({'success': False, 'error': 'No image provided'})

@login_required
def analyze_chart_data(request, symbol):
    try:
        session = TradingSession.objects.get(user=request.user, is_active=True)
        client = UpstoxAPI(session.access_token)
        historical = client.get_historical(symbol, days=100)
        if not historical:
            return JsonResponse({'success': False, 'error': 'No data'})
        
        chart_analysis = chart_reader.read_chart_from_data(historical)
        df = pd.DataFrame(historical)
        engine = StrategyEngine(symbol)
        signal = engine.get_final_signal(df)
        
        return JsonResponse({'success': True, 'chart_analysis': chart_analysis, 'trading_signal': signal})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def generate_live_chart(request, symbol):
    try:
        session = TradingSession.objects.get(user=request.user, is_active=True)
        client = UpstoxAPI(session.access_token)
        historical = client.get_historical(symbol, days=30)
        if not historical:
            return JsonResponse({'success': False, 'error': 'No data'})
        
        df = pd.DataFrame(historical)
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name=symbol), row=1, col=1)
        
        df['sma_10'] = df['close'].rolling(10).mean()
        df['sma_20'] = df['close'].rolling(20).mean()
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['sma_10'], name='SMA 10', line=dict(color='orange')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['sma_20'], name='SMA 20', line=dict(color='blue')), row=1, col=1)
        
        colors = ['red' if row['close'] < row['open'] else 'green' for _, row in df.iterrows()]
        fig.add_trace(go.Bar(x=df['timestamp'], y=df['volume'], name='Volume', marker_color=colors), row=2, col=1)
        
        fig.update_layout(title=f'{symbol} - Live Chart', yaxis_title='Price (₹)', template='plotly_dark', height=700)
        chart_html = fig.to_html(full_html=False)
        return JsonResponse({'success': True, 'chart': chart_html})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_pattern_statistics(request):
    return JsonResponse({
        'success': True,
        'patterns': {
            'head_shoulders': {'detected': 12, 'success_rate': 75},
            'double_top': {'detected': 8, 'success_rate': 62.5},
            'double_bottom': {'detected': 10, 'success_rate': 80},
            'triangle': {'detected': 15, 'success_rate': 66.7}
        }
    })

@login_required
def get_performance(request):
    days = int(request.GET.get('days', 30))
    start_date = datetime.now().date() - timedelta(days=days)
    
    daily = DailyPerformance.objects.filter(user=request.user, date__gte=start_date).order_by('date')
    daily_data = [{
        'date': d.date.strftime('%Y-%m-%d'),
        'pnl': d.pnl,
        'pnl_percent': d.pnl_percent,
        'trades': d.trades_count,
        'win_rate': d.win_rate
    } for d in daily]
    
    trades = Trade.objects.filter(user=request.user, status='EXECUTED')
    total_trades = trades.count()
    winning_trades = trades.filter(pnl__gt=0).count()
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    total_pnl = trades.aggregate(total=Sum('pnl'))['total'] or 0
    avg_win = trades.filter(pnl__gt=0).aggregate(avg=Avg('pnl'))['avg'] or 0
    avg_loss = abs(trades.filter(pnl__lt=0).aggregate(avg=Avg('pnl'))['avg'] or 0)
    profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
    
    best_trade = trades.order_by('-pnl').first()
    worst_trade = trades.order_by('pnl').first()
    
    return JsonResponse({
        'success': True,
        'metrics': {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': round(win_rate, 2),
            'total_pnl': round(total_pnl, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'best_trade': {'pnl': round(best_trade.pnl, 2), 'symbol': best_trade.symbol.symbol} if best_trade else None,
            'worst_trade': {'pnl': round(worst_trade.pnl, 2), 'symbol': worst_trade.symbol.symbol} if worst_trade else None,
            'daily_performance': daily_data
        }
    })

@login_required
def get_notifications(request):
    limit = int(request.GET.get('limit', 20))
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:limit]
    notification_data = [{
        'id': n.id,
        'type': n.type,
        'title': n.title,
        'message': n.message,
        'is_read': n.is_read,
        'time': n.created_at.strftime('%Y-%m-%d %H:%M:%S')
    } for n in notifications]
    return JsonResponse({'success': True, 'notifications': notification_data})