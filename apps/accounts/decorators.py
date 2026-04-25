from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

def role_required(allowed_roles):
    """
    Decorator for views that checks if the user's Profile has one of the allowed roles.
    Bypasses check for superusers.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            # Superusers have full access
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Check UserProfile for the assigned role
            user_role = None
            if hasattr(request.user, 'profile') and request.user.profile.role:
                user_role = request.user.profile.role.name

            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)

            # Raise 403 if role doesn't match
            raise PermissionDenied("You do not have permission to access this resource.")
        
        return _wrapped_view
    return decorator

# Convenience Shortcuts
admin_only = role_required(['Admin'])
accountant_only = role_required(['Accountant'])
manager_only = role_required(['Manager'])
