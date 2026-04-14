from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime

class TradingSession(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=500)
    user_id = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {'Active' if self.is_active else 'Inactive'}"

class NSEStock(models.Model):
    symbol = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200, blank=True)
    sector = models.CharField(max_length=100, blank=True, db_index=True)
    isin = models.CharField(max_length=20, blank=True)
    series = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['sector', 'is_active']),
            models.Index(fields=['symbol', 'is_active']),
        ]
    
    def __str__(self):
        return self.symbol

class Trade(models.Model):
    SIDE_CHOICES = [('BUY', 'Buy'), ('SELL', 'Sell')]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('EXECUTED', 'Executed'),
        ('PARTIAL', 'Partially Executed'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    symbol = models.ForeignKey(NSEStock, on_delete=models.CASCADE)
    side = models.CharField(max_length=4, choices=SIDE_CHOICES)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.FloatField()
    executed_price = models.FloatField(null=True, blank=True)
    executed_quantity = models.IntegerField(default=0)
    order_id = models.CharField(max_length=100, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    pnl = models.FloatField(default=0)
    pnl_percent = models.FloatField(default=0)
    slippage = models.FloatField(default=0)
    signal_confidence = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['symbol', 'status']),
        ]
    
    @property
    def value(self):
        return self.quantity * self.price

class Position(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    symbol = models.ForeignKey(NSEStock, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    avg_price = models.FloatField()
    current_price = models.FloatField(default=0)
    unrealized_pnl = models.FloatField(default=0)
    realized_pnl = models.FloatField(default=0)
    stop_loss = models.FloatField(null=True, blank=True)
    target = models.FloatField(null=True, blank=True)
    entry_time = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'symbol']
        indexes = [
            models.Index(fields=['user', 'symbol']),
        ]
    
    @property
    def pnl(self):
        return (self.current_price - self.avg_price) * self.quantity if self.current_price else 0

class Signal(models.Model):
    SIGNAL_CHOICES = [('BUY', 'Buy'), ('SELL', 'Sell'), ('HOLD', 'Hold')]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    symbol = models.ForeignKey(NSEStock, on_delete=models.CASCADE)
    signal = models.CharField(max_length=4, choices=SIGNAL_CHOICES)
    confidence = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    price = models.FloatField()
    ml_score = models.FloatField(default=0)
    technical_score = models.FloatField(default=0)
    momentum_score = models.FloatField(default=0)
    mean_reversion_score = models.FloatField(default=0)
    rsi = models.FloatField(null=True)
    macd = models.FloatField(null=True)
    volume_ratio = models.FloatField(null=True)
    volatility = models.FloatField(null=True)
    reason = models.TextField(blank=True)
    executed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'symbol', 'created_at']),
            models.Index(fields=['signal', 'confidence']),
        ]

class DailyPerformance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    starting_balance = models.FloatField()
    ending_balance = models.FloatField()
    pnl = models.FloatField()
    pnl_percent = models.FloatField()
    trades_count = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    losing_trades = models.IntegerField(default=0)
    win_rate = models.FloatField(default=0)
    max_drawdown = models.FloatField(default=0)
    
    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']

class StopLossOrder(models.Model):
    trade = models.ForeignKey(Trade, on_delete=models.CASCADE, related_name='stop_losses')
    symbol = models.ForeignKey(NSEStock, on_delete=models.CASCADE)
    trigger_price = models.FloatField()
    quantity = models.IntegerField()
    status = models.CharField(max_length=20, default='ACTIVE')
    triggered_at = models.DateTimeField(null=True, blank=True)
    order_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['symbol', 'status']),
        ]

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

