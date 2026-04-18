"""
Accounts service layer.

All business logic for user management lives here.
Views MUST NOT contain business logic — they delegate to these functions.

Architecture: Views → Services → Models
"""

import logging

from django.contrib.auth.models import Group
from django.db import transaction

from .models import User

logger = logging.getLogger(__name__)


@transaction.atomic
def create_user_with_group(*, username, email, password, group_name):
    """
    Create a new user and assign them to a Django Group.

    This is the ONLY correct way to create users in the system.
    Do not use User.objects.create_user() directly in views.

    Args:
        username: Unique username.
        email: User's email address.
        password: Raw password (will be hashed by the manager).
        group_name: Name of the group to assign (e.g., 'Admin', 'Accountant').

    Returns:
        User: The created user instance.

    Raises:
        ValueError: If group_name is not a recognized role.
    """
    VALID_GROUPS = ['Admin', 'Accountant']

    if group_name not in VALID_GROUPS:
        raise ValueError(
            f'Invalid group: "{group_name}". Must be one of: {VALID_GROUPS}'
        )

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
    )

    group, created = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)

    if created:
        logger.info('Created new group: %s', group_name)

    logger.info(
        'Created user "%s" and assigned to group "%s".',
        username,
        group_name,
    )

    return user


def get_users_by_group(group_name):
    """
    Retrieve all active users belonging to a specific group.

    Args:
        group_name: Name of the Django group.

    Returns:
        QuerySet of User instances.
    """
    return User.objects.filter(
        groups__name=group_name,
        is_active=True,
    ).select_related().prefetch_related('groups')


def assign_user_to_group(*, user, group_name):
    """
    Add a user to an additional group.

    Args:
        user: User instance.
        group_name: Name of the group to add.

    Returns:
        Group: The group instance.
    """
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)

    logger.info('Assigned user "%s" to group "%s".', user.username, group_name)
    return group


def remove_user_from_group(*, user, group_name):
    """
    Remove a user from a group.

    Args:
        user: User instance.
        group_name: Name of the group to remove.
    """
    try:
        group = Group.objects.get(name=group_name)
        user.groups.remove(group)
        logger.info('Removed user "%s" from group "%s".', user.username, group_name)
    except Group.DoesNotExist:
        logger.warning('Group "%s" does not exist.', group_name)
