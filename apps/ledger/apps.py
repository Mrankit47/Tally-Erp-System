from django.apps import AppConfig


class LedgerConfig(AppConfig):
    """Chart of accounts and ledger balance management."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ledger'
    verbose_name = 'Ledger'
