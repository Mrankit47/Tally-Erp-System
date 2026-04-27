"""
Custom User model for the ERP system.

IMPORTANT: This model does NOT have a 'role' field.
Roles are managed entirely through Django's Group system.
Users are assigned to groups like 'Admin' or 'Accountant' via the service layer.

This design is scalable because:
- New roles can be added without schema changes (no migrations).
- A user can belong to multiple groups simultaneously.
- Django's built-in Permission system integrates natively with Groups.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import CustomUserManager


class User(AbstractUser):
    """
    Custom user model for the ERP system.

    Extends Django's AbstractUser with additional profile fields.
    Role-based access is handled via Django Groups — NOT a model field.

    Groups used:
        - 'Admin': Full system access.
        - 'Accountant': Access to financial modules.
    """

    # Profile fields
    phone = models.CharField(
        max_length=15,
        blank=True,
        default='',
        help_text='Contact phone number.',
    )

    # Use our custom manager
    objects = CustomUserManager()

    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return f'{self.username} ({self.email})'

    @property
    def role_names(self):
        """Return a list of group names this user belongs to."""
        return list(self.groups.values_list('name', flat=True))

    @property
    def is_admin_role(self):
        """Check if user is in the Admin group."""
        return self.groups.filter(name='Admin').exists()

    @property
    def is_accountant_role(self):
        """Check if user is in the Accountant group."""
        return self.groups.filter(name='Accountant').exists()


class Role(models.Model):
    """System roles for access control."""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """Extension of the User model to store role and other profile info."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile ({self.role})"
