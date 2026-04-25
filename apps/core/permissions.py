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

def role_required(allowed_roles):
    """
    Decorator for views that checks if the user has one of the allowed roles.
    Superusers bypass all checks.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Check for role in profile
            user_role = None
            if hasattr(request.user, 'profile') and request.user.profile.role:
                user_role = request.user.profile.role.name
                
            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)
                
            raise PermissionDenied("You do not have the required role to access this page.")
        return _wrapped_view
    return decorator

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

