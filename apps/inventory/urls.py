"""URL routing for the inventory app."""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.stock_item_list_view, name='inventory_list'),
    path('new/', views.stock_item_create_view, name='inventory_create'),
]
