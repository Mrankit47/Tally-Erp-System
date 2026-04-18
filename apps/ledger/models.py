"""
Ledger models.

Defines the Chart of Accounts. 
Ledgers are grouped hierarchically (e.g., Cash -> Bank Accounts -> Current Assets).
"""

from django.db import models
from django.db.models import Sum
from core.models import TenantModel


class LedgerGroup(TenantModel):
    """
    Groups ledgers together (e.g., 'Indirect Expenses', 'Bank Accounts').
    """
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subgroups'
    )

    class Meta:
        verbose_name = 'Ledger Group'
        verbose_name_plural = 'Ledger Groups'
        unique_together = ['company', 'name']
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class Ledger(TenantModel):
    """
    Individual accounts (e.g., 'HDFC Bank', 'Office Rent').
    Balances are calculated dynamically from voucher entries.
    """
    name = models.CharField(max_length=255)
    group = models.ForeignKey(
        LedgerGroup,
        on_delete=models.PROTECT,
        related_name='ledgers'
    )
    opening_balance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text='Balance at the start of the relationship.'
    )

    class Meta:
        verbose_name = 'Ledger'
        verbose_name_plural = 'Ledgers'
        unique_together = ['company', 'name']
        ordering = ['name']
        indexes = [
            models.Index(fields=['company', 'group']),
        ]

    def __str__(self):
        return f"{self.name} | {self.company.name}"

    @property
    def balance(self):
        """
        Dynamically calculate current balance.
        Balance = Opening + Sum(Debits) - Sum(Credits)
        """
        from voucher.models import VoucherEntry, EntryType
        
        entries = VoucherEntry.objects.filter(ledger=self)
        debits = entries.filter(entry_type=EntryType.DEBIT).aggregate(total=Sum('amount'))['total'] or 0
        credits = entries.filter(entry_type=EntryType.CREDIT).aggregate(total=Sum('amount'))['total'] or 0
        
        return self.opening_balance + debits - credits
