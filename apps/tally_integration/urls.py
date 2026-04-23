"""URL routing for the tally_integration app."""

from django.urls import path
from . import views

urlpatterns = [
    path('sync/ledgers/', views.sync_ledgers_view, name='sync_ledgers'),
    path('sync/voucher/<uuid:voucher_id>/', views.sync_single_voucher_view, name='sync_single_voucher'),
    path('sync-log/<uuid:log_id>/delete/', views.delete_sync_log_view, name='delete_sync_log'),
]
