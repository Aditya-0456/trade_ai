from django.urls import path
from . import views
from .views import home

urlpatterns = [
    path('logout/', views.logout_view, name='logout'),
    path('connect/', views.connect_upstox, name='connect'),
    path('disconnect/', views.disconnect_upstox, name='disconnect'),
    path('signals/', views.get_signals, name='signals'),
    path('trade/', views.execute_trade, name='trade'),
    path('positions/', views.get_positions, name='positions'),
    path('trades/', views.get_trades, name='trades'),
    path('balance/', views.get_balance, name='balance'),
    path('close-position/', views.close_position, name='close_position'),
    path('upload-chart/', views.upload_chart, name='upload_chart'),
    path('analyze-chart/<str:symbol>/', views.analyze_chart_data, name='analyze_chart'),
    path('live-chart/<str:symbol>/', views.generate_live_chart, name='live_chart'),
    path('pattern-stats/', views.get_pattern_statistics, name='pattern_stats'),
    path('charts/', views.charts_page, name='charts'),
    path('performance/', views.get_performance, name='performance'),
    path('notifications/', views.get_notifications, name='notifications'),
]