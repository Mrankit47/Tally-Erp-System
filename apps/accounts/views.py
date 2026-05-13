"""
Accounts views.

These views are THIN. They handle HTTP concerns only:
- Parse request data
- Validate via serializers
- Delegate to the service layer
- Return the response

Architecture: Views → Services → Models
"""

import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsAdmin

from . import services
from .models import User
from .serializers import (
    UserCreateSerializer,
    UserDetailSerializer,
    UserListSerializer,
)

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user management.

    list:       GET    /api/v1/accounts/users/
    create:     POST   /api/v1/accounts/users/
    retrieve:   GET    /api/v1/accounts/users/{id}/
    update:     PUT    /api/v1/accounts/users/{id}/
    partial:    PATCH  /api/v1/accounts/users/{id}/
    destroy:    DELETE /api/v1/accounts/users/{id}/
    me:         GET    /api/v1/accounts/users/me/
    """

    queryset = User.objects.filter(is_active=True).prefetch_related('groups')
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_serializer_class(self):
        """Return the appropriate serializer based on the action."""
        if self.action == 'create':
            return UserCreateSerializer
        if self.action == 'list':
            return UserListSerializer
        return UserDetailSerializer

    def create(self, request, *args, **kwargs):
        """
        Create a new user via the service layer.

        The view only validates input — all business logic is in services.py.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Delegate to service layer
        user = services.create_user_with_group(
            username=serializer.validated_data['username'],
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            group_name=serializer.validated_data['group_name'],
        )

        output_serializer = UserDetailSerializer(user)
        return Response(
            {'success': True, 'data': output_serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Return the currently authenticated user's profile."""
        serializer = UserDetailSerializer(request.user)
        return Response({'success': True, 'data': serializer.data})
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .decorators import admin_only
from .models import User, UserProfile, Role
from django.contrib import messages

@login_required
@admin_only
def user_management_view(request):
    """List all non-superuser users and their roles for management."""
    users = User.objects.filter(is_superuser=False).select_related('profile__role')
    roles = Role.objects.all()
    context = {
        'users': users,
        'roles': roles,
    }
    return render(request, 'accounts/user_management.html', context)

@login_required
@admin_only
def update_user_role(request):
    """Update a user's role from the dashboard."""
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        role_id = request.POST.get('role_id')
        
        user = get_object_or_404(User, id=user_id)
        role = get_object_or_404(Role, id=role_id)
        
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.save()
        
        messages.success(request, f"Role for {user.username} updated to {role.name}.")
    
    return redirect('user_management')

@login_required
@admin_only
def role_management_view(request):
    """Create and list roles from the dashboard."""
    if request.method == 'POST':
        role_name = request.POST.get('role_name')
        if role_name:
            Role.objects.get_or_create(name=role_name)
            messages.success(request, f"Role '{role_name}' created successfully.")
            
    roles = Role.objects.all()
    return render(request, 'accounts/role_management.html', {'roles': roles})
@login_required
@admin_only
def create_user_dashboard_view(request):
    """Create a new system user from the dashboard."""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role_id = request.POST.get('role_id')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            if role_id:
                role = Role.objects.get(id=role_id)
                profile, _ = UserProfile.objects.get_or_create(user=user)
                profile.role = role
                profile.save()
            messages.success(request, f"User {username} created successfully.")
            
    return redirect('user_management')
