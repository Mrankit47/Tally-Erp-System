"""
RBAC Role definitions and Permissions.
"""
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

def in_groups(user, roles):
    """
    Evaluates if a user belongs to any of the requested roles.
    Superusers automatically bypass Role-Based Access Control logic.
    """
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=roles).exists()

def role_required(roles):
    """
    Decorator for views that checks if the user belongs to the specified groups.
    If not, raises an immediate 403 Permission Denied.
    Usage: @role_required(['Admin', 'Accountant'])
    """
    def check_role(user):
        if not user.is_authenticated:
            return False
        if in_groups(user, roles):
            return True
        raise PermissionDenied("You do not have the required clearance to access this financial resource.")
        
    return user_passes_test(check_role)

# =============================================================================
# REST FRAMEWORK PERMISSIONS
# =============================================================================
from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    """
    DRF permission class that only allows staff users (Superusers or Admins).
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)

