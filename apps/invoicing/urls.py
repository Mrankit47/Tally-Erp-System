from django.urls import path
from . import views

urlpatterns = [
    path('invoice/<uuid:voucher_id>/pdf/', views.download_invoice_pdf, name='invoice_pdf_download'),
]
