"""
Custom DRF permission classes.

These permissions use Django's Group system for role-based access control.
Users are assigned to groups (e.g., "Admin", "Accountant") via the service layer.
"""

from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """
    Allow access only to users in the 'Admin' group.

    Usage in a ViewSet:
        permission_classes = [IsAuthenticated, IsAdmin]
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.groups.filter(name='Admin').exists()


class IsAccountant(BasePermission):
    """
    Allow access only to users in the 'Accountant' group.

    Usage in a ViewSet:
        permission_classes = [IsAuthenticated, IsAccountant]
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.groups.filter(name='Accountant').exists()


class IsAdminOrAccountant(BasePermission):
    """
    Allow access to users in either the 'Admin' or 'Accountant' group.

    Useful for endpoints that both roles can access, such as read-only reports.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.groups.filter(name__in=['Admin', 'Accountant']).exists()
