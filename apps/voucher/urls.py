from django.urls import path
from . import views

urlpatterns = [
    path('sales/', views.voucher_list_view, {'voucher_type': 'sales'}, name='sales_list'),
    path('sales/new/', views.voucher_create_view, {'voucher_type': 'sales'}, name='sales_create'),
    
    path('payments/', views.voucher_list_view, {'voucher_type': 'payments'}, name='payments_list'),
    path('payments/new/', views.voucher_create_view, {'voucher_type': 'payments'}, name='payments_create'),
    
    path('receipts/', views.voucher_list_view, {'voucher_type': 'receipts'}, name='receipts_list'),
    path('receipts/new/', views.voucher_create_view, {'voucher_type': 'receipts'}, name='receipts_create'),
    
    path('purchases/', views.voucher_list_view, {'voucher_type': 'purchases'}, name='purchases_list'),
    path('purchases/new/', views.voucher_create_view, {'voucher_type': 'purchases'}, name='purchases_create'),
    
    path('journals/', views.voucher_list_view, {'voucher_type': 'journal'}, name='journal_list'),
    path('journals/new/', views.voucher_create_view, {'voucher_type': 'journal'}, name='journal_create'),
    
    # AI Invoice Scanner
    path('scan/', views.voucher_scan_view, name='voucher_scan'),
    path('scan/api/', views.voucher_scan_api, name='voucher_scan_api'),
    path('scan/save/', views.voucher_scan_save_api, name='voucher_scan_save_api'),
    
    # AI Financial Analytics & Insights Dashboard
    path('analytics/', views.voucher_analytics_view, name='voucher_analytics'),
    path('analytics/api/', views.voucher_analytics_api, name='voucher_analytics_api'),
    
    # Approval Workflow
    path('approve-voucher/<uuid:voucher_id>/', views.approve_voucher_view, name='approve_voucher'),
    
    # Detail View
    path('view/<uuid:voucher_id>/', views.voucher_detail_view, name='voucher_detail'),
]
