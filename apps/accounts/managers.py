"""
Custom user manager for the ERP system.

Ensures consistent user creation with proper email normalization
and validation. Used by the custom User model.
"""

from django.contrib.auth.models import BaseUserManager


class CustomUserManager(BaseUserManager):
    """
    Custom manager for User model.

    Overrides create_user and create_superuser to enforce:
    - Email is always normalized (lowercase domain).
    - Username is required.
    - Superusers always get is_staff=True and is_superuser=True.
    """

    def create_user(self, username, email=None, password=None, **extra_fields):
        """
        Create and return a regular user.

        Args:
            username: Required. Unique username.
            email: Optional. User's email address.
            password: Raw password (will be hashed).
            **extra_fields: Additional model fields.

        Returns:
            User instance.

        Raises:
            ValueError: If username is not provided.
        """
        if not username:
            raise ValueError('Users must have a username.')

        if email:
            email = self.normalize_email(email)

        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """
        Create and return a superuser.

        Superusers always have is_staff=True and is_superuser=True.

        Raises:
            ValueError: If is_staff or is_superuser is explicitly set to False.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, email, password, **extra_fields)
