from django.apps import AppConfig


class TallyIntegrationConfig(AppConfig):
    """Tally ERP data synchronization and XML exchange."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tally_integration'
    verbose_name = 'Tally Integration'
