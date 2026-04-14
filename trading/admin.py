from django.contrib import admin
from django.contrib import admin
from .models import TradingSession, NSEStock, Trade, Position

admin.site.register(TradingSession)
admin.site.register(NSEStock)
admin.site.register(Trade)
admin.site.register(Position)

# Register your models here.
