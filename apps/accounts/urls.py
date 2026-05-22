"""
URL routing for the accounts app.

Uses DRF's DefaultRouter for automatic URL generation from ViewSets.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UserViewSet, 
    user_management_view, 
    role_management_view, 
    update_user_role,
    create_user_dashboard_view,
    edit_profile_view
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include('django.contrib.auth.urls')),
    path('api/v1/', include(router.urls)),
    
    # Dashboard Management UI
    path('manage/users/', user_management_view, name='user_management'),
    path('manage/roles/', role_management_view, name='role_management'),
    path('manage/users/update-role/', update_user_role, name='update_user_role'),
    path('manage/users/create/', create_user_dashboard_view, name='create_user_dashboard'),
    path('profile/edit/', edit_profile_view, name='edit_profile'),
]
