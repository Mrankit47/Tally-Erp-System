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
    alias = models.CharField(max_length=255, blank=True, null=True, help_text='Alternative name for the group.')
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
    alias = models.CharField(max_length=255, blank=True, null=True)
    group = models.ForeignKey(
        LedgerGroup,
        on_delete=models.PROTECT,
        related_name='ledgers'
    )
    # Mailing Details
    address = models.TextField(blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, default='India')
    pincode = models.CharField(max_length=20, blank=True, null=True)
    
    # Tax Details
    pan_no = models.CharField(max_length=20, blank=True, null=True)
    gstin = models.CharField(max_length=20, blank=True, null=True)
    
    opening_balance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text='Balance at the start of the relationship.'
    )
    credit_limit = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Maximum allowed credit limit (for Debtors/Creditors).'
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


class Currency(TenantModel):
    """
    Accounting Currency Master (e.g. ₹, $, £).
    """
    symbol = models.CharField(max_length=10)
    formal_name = models.CharField(max_length=50)
    number_of_decimal_places = models.PositiveSmallIntegerField(default=2)
    exchange_rate = models.DecimalField(
        max_digits=20, decimal_places=6, default=1.0,
        help_text="Standard exchange rate relative to the base currency."
    )

    class Meta:
        verbose_name = 'Currency'
        verbose_name_plural = 'Currencies'
        unique_together = ['company', 'symbol']
        ordering = ['formal_name']

    def __str__(self):
        return f"{self.formal_name} ({self.symbol})"


class Budget(TenantModel):
    """
    Budgets and Controls Master.
    Allows setting target amounts for ledgers or groups over a specific period.
    """
    name = models.CharField(max_length=255)
    from_date = models.DateField()
    to_date = models.DateField()
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    ledger = models.ForeignKey(
        Ledger, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='budgets'
    )
    group = models.ForeignKey(
        LedgerGroup, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='budgets'
    )

    class Meta:
        verbose_name = 'Budget'
        verbose_name_plural = 'Budgets'
        unique_together = ['company', 'name']
        ordering = ['name']

    def __str__(self):
        return f"{self.name} | {self.amount}"


class Scenario(TenantModel):
    """
    Scenario Master for Management Reporting.
    Used for provisional/optional vouchers that shouldn't affect actual books.
    """
    name = models.CharField(max_length=255)
    include_actuals = models.BooleanField(
        default=True,
        help_text="Include actual vouchers in this scenario's reporting."
    )
    exclude_forex_gains = models.BooleanField(
        default=False,
        help_text="Exclude forex gain/loss calculations."
    )

    class Meta:
        verbose_name = 'Scenario'
        verbose_name_plural = 'Scenarios'
        unique_together = ['company', 'name']
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.company.name})"
