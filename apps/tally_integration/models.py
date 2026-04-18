from django.db import models
from core.models import TenantModel


class SyncOperation(models.TextChoices):
    """Direction of synchronization."""
    FETCH = 'FETCH', 'Fetch from Tally'
    PUSH = 'PUSH', 'Push to Tally'


class SyncStatus(models.TextChoices):
    """Outcome of the synchronization attempt."""
    SUCCESS = 'SUCCESS', 'Success'
    FAILED = 'FAILED', 'Failed'


class SyncLog(TenantModel):
    """
    Audit log for recording Tally synchronization events.
    
    Scoped to a Company and tracks exactly what happened during a sync.
    """
    model_name = models.CharField(
        max_length=100,
        help_text='The model being synced (e.g., Ledger, Voucher).'
    )
    operation = models.CharField(
        max_length=10,
        choices=SyncOperation.choices,
        db_index=True
    )
    status = models.CharField(
        max_length=10,
        choices=SyncStatus.choices,
        db_index=True
    )
    message = models.TextField(
        blank=True,
        help_text='Summary of the operation result or error message.'
    )
    response_xml = models.TextField(
        blank=True,
        null=True,
        help_text='Raw XML response snippet from Tally (useful for debugging failures).'
    )
    records_affected = models.IntegerField(
        default=0,
        help_text='Number of records successfully processed.'
    )

    class Meta:
        verbose_name = 'Sync Log'
        verbose_name_plural = 'Sync Logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.operation} {self.model_name} | {self.status} | {self.created_at}"
