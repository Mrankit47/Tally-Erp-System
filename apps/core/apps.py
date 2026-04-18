from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Core application providing shared utilities across the ERP system."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core'
