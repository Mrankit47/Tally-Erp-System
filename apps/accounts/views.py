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
