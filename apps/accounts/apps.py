from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """User authentication and role-based access control."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'Accounts & Authentication'

    def ready(self):
        from . import signals
