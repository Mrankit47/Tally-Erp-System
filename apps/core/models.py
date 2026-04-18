"""
Core models and base classes for the ERP system.

Provides:
- BaseModel: audit fields, soft-delete, and standard timestamps.
- TenantModel: multi-tenancy (company isolation) and Tally sync fields.
- ActiveManager: custom manager that filters out soft-deleted records.
"""

import uuid
from django.db import models
from django.conf import settings


class ActiveManager(models.Manager):
    """
    Custom manager that automatically filters out records where is_active=False.
    Use this for standard queries. Use `all_objects` to bypass the filter.
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class SyncStatus(models.TextChoices):
    """Enumeration of Tally synchronization states."""
    PENDING = 'PENDING', 'Pending'
    SYNCED = 'SYNCED', 'Synced'
    FAILED = 'FAILED', 'Failed'


class BaseModel(models.Model):
    """
    Abstract base model with professional Audit Trail and Soft-Delete capabilities.

    All domain models should inherit from this to ensure consistent behavior.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='Unique identifier for this record.'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='Timestamp when this record was created.'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Timestamp when this record was last modified.'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="%(class)s_created",
        null=True,
        blank=True,
        help_text='The user who created this record.'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="%(class)s_updated",
        null=True,
        blank=True,
        help_text='The user who last updated this record.'
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Soft-delete flag. Inactive records are hidden by default.'
    )

    # Managers
    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def soft_delete(self):
        """Mark this record as inactive instead of deleting it."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])


class TenantModel(BaseModel):
    """
    Abstract base class for models that require Company isolation and Tally sync.

    Ensures that data is scoped to a specific company (multi-tenancy) and
    tracks synchronization status for external integrations.
    """

    company = models.ForeignKey(
        'company.Company',
        on_delete=models.CASCADE,
        related_name='%(class)s_records',
        db_index=True,
        help_text='The company this record belongs to.'
    )
    sync_status = models.CharField(
        max_length=20,
        choices=SyncStatus.choices,
        default=SyncStatus.PENDING,
        db_index=True,
        help_text='Status of synchronization with Tally.'
    )
    tally_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text='External ID mapping to the Tally record.'
    )
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp of the last successful synchronization.'
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['company', 'created_at']),
        ]
