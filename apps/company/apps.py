from django.apps import AppConfig


class CompanyConfig(AppConfig):
    """Company and branch management for the ERP system."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'company'
    verbose_name = 'Company Management'
