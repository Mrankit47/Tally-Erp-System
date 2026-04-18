from django.urls import path
from . import views

urlpatterns = [
    path('ledgers/', views.ledger_list_view, name='ledger_list'),
    path('ledgers/new/', views.ledger_create_view, name='ledger_create'),
]
