"""
Inventory models.

Defines stock items and tracking of inventory movements.
Integrated with the voucher system for automated accounting.
"""

from django.db import models
from django.db.models import Sum
from core.models import TenantModel, SyncStatus as ModelSyncStatus
from django.utils import timezone


class StockItem(TenantModel):
    """
    Items or products managed in the inventory.
    """
    name = models.CharField(max_length=255)
    unit_of_measure = models.CharField(
        max_length=50,
        default='Nos',
        help_text='e.g., Kgs, Pcs, Nos.'
    )
    opening_stock_qty = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text='Initial stock quantity.'
    )

    # ─── SYNC FIELDS ───
    sync_status = models.CharField(
        max_length=20,
        choices=ModelSyncStatus.choices,
        default=ModelSyncStatus.PENDING,
        db_index=True
    )
    tally_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text='Matching name or ID in Tally ERP'
    )
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Stock Item'
        verbose_name_plural = 'Stock Items'
        unique_together = ['company', 'name']
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.company.name})"

    @property
    def current_quantity(self):
        """
        Dynamically calculate stock quantity.
        Stock = Opening + Sum(IN) - Sum(OUT)
        """
        from .models import TransactionType
        
        txs = self.transactions.all()
        ins = txs.filter(transaction_type=TransactionType.IN).aggregate(total=Sum('quantity'))['total'] or 0
        outs = txs.filter(transaction_type=TransactionType.OUT).aggregate(total=Sum('quantity'))['total'] or 0
        
        return self.opening_stock_qty + ins - outs


class TransactionType(models.TextChoices):
    """Inventory movement direction."""
    IN = 'IN', 'Inward (Stock In)'
    OUT = 'OUT', 'Outward (Stock Out)'


class StockTransaction(TenantModel):
    """
    Records movement of a specific stock item.
    """
    stock_item = models.ForeignKey(
        StockItem,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    voucher_entry = models.ForeignKey(
        'voucher.VoucherEntry',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='stock_transactions',
        help_text='Optional link to the accounting entry.'
    )
    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text='Quantity moved.'
    )
    rate = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text='Rate per unit.'
    )
    transaction_type = models.CharField(
        max_length=3,
        choices=TransactionType.choices,
        db_index=True
    )

    class Meta:
        verbose_name = 'Stock Transaction'
        verbose_name_plural = 'Stock Transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'stock_item', 'transaction_type']),
        ]

    def __str__(self):
        return f"{self.transaction_type} {self.quantity} {self.stock_item.name}"
