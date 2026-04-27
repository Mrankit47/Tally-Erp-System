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
    
    # Approval Workflow
    path('approve-voucher/<uuid:voucher_id>/', views.approve_voucher_view, name='approve_voucher'),
    
    # Detail View
    path('view/<uuid:voucher_id>/', views.voucher_detail_view, name='voucher_detail'),
]
