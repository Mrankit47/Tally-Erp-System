"""
Company models.

Defines the enterprise structure. Each record represents a business entity
with its own financial period and settings.
"""

from django.db import models
from core.models import BaseModel


class Company(BaseModel):
    """
    Represents a business entity or enterprise.
    """
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text='Full legal name of the company.'
    )
    tax_id = models.CharField(
        max_length=50,
        blank=True,
        help_text='GSTIN/VAT or other tax identification number.'
    )
    address = models.TextField(
        blank=True,
        help_text='Registered office address.'
    )
    currency = models.CharField(
        max_length=10,
        default='INR',
        help_text='Base currency (e.g., INR, USD).'
    )
    financial_year_start = models.DateField(
        help_text='Start date of the current financial year.'
    )
    financial_year_end = models.DateField(
        help_text='End date of the current financial year.'
    )

    class Meta:
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'
        ordering = ['name']

    def __str__(self):
        return self.name
