"""URL routing for the reports app."""

from django.urls import path
from .views import (
    trial_balance_view,
    profit_loss_view,
    export_trial_balance_csv,
    export_profit_loss_csv
)

app_name = 'reports'

urlpatterns = [
    path('trial-balance/', trial_balance_view, name='trial_balance'),
    path('profit-loss/', profit_loss_view, name='profit_loss'),
    path('trial-balance/export/', export_trial_balance_csv, name='export_trial_balance_csv'),
    path('profit-loss/export/', export_profit_loss_csv, name='export_profit_loss_csv'),
]
