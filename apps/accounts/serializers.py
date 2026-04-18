"""
DRF serializers for the accounts app.

Serializers handle validation and transformation of User data
for API requests and responses.
"""

from django.contrib.auth.models import Group
from rest_framework import serializers

from .models import User


class GroupSerializer(serializers.ModelSerializer):
    """Serializer for Django Group model."""

    class Meta:
        model = Group
        fields = ['id', 'name']


class UserListSerializer(serializers.ModelSerializer):
    """
    Serializer for user list endpoints.

    Returns a summary of user data including their assigned groups.
    """

    groups = GroupSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'is_active', 'date_joined', 'groups',
        ]
        read_only_fields = ['id', 'date_joined']


class UserCreateSerializer(serializers.Serializer):
    """
    Serializer for user creation.

    This is a plain Serializer (not ModelSerializer) because user creation
    is handled by the service layer, not by the serializer's save() method.
    """

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    group_name = serializers.ChoiceField(choices=['Admin', 'Accountant'])

    def validate_username(self, value):
        """Ensure username is unique."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('A user with this username already exists.')
        return value

    def validate_email(self, value):
        """Ensure email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for user detail/update endpoints.

    Includes all user fields and their group memberships.
    """

    groups = GroupSerializer(many=True, read_only=True)
    role_names = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'is_active', 'date_joined', 'last_login',
            'groups', 'role_names',
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']
