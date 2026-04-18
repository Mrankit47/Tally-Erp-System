"""
Django admin configuration for the accounts app.

Registers the custom User model with group management
directly accessible from the admin interface.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin for the User model.

    Extends Django's built-in UserAdmin to include:
    - Phone field in the user form.
    - Group assignments visible in the list display.
    - Filtering by groups (roles).
    """

    # List display
    list_display = [
        'username', 'email', 'first_name', 'last_name',
        'get_groups', 'is_active', 'is_staff', 'date_joined',
    ]
    list_filter = ['is_active', 'is_staff', 'groups', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']

    # Form fieldsets
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile', {
            'fields': ('phone',),
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Profile', {
            'fields': ('email', 'phone'),
        }),
        ('Roles', {
            'fields': ('groups',),
        }),
    )

    def get_groups(self, obj):
        """Display group names as a comma-separated string."""
        return ', '.join(obj.groups.values_list('name', flat=True))

    get_groups.short_description = 'Roles'
