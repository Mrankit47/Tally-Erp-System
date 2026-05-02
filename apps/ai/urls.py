from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_endpoint, name='chat_endpoint'),
]
