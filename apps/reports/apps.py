from django.apps import AppConfig


class ReportsConfig(AppConfig):
    """Financial and inventory reporting module."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reports'
    verbose_name = 'Reports'
