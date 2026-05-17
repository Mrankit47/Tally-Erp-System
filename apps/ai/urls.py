from django.urls import path
from . import views

app_name = 'ai'

urlpatterns = [
    path('', views.chat_endpoint, name='chat_endpoint'),
    path('audit/resolve/', views.resolve_audit_risk_api, name='resolve_audit_risk'),
]
