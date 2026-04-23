"""URL routing for the company app."""

from django.urls import path
from . import views

urlpatterns = [
    path('api/fetch-tally-companies/', views.fetch_tally_companies_view, name='api_fetch_tally_companies'),
    path('api/select-company/', views.select_company_view, name='api_select_company'),
]
