"""
URL routing for the accounts app.

Uses DRF's DefaultRouter for automatic URL generation from ViewSets.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import UserViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
]
