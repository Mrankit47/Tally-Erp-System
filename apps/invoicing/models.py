from django.db import models, transaction
from django.utils import timezone
from core.models import TenantModel


class Invoice(TenantModel):
    """
    Legal Invoice document linked to a Sales Voucher.
    Stores a snapshot of financial and customer data at the time of issuance.
    """
    voucher = models.OneToOneField(
        'voucher.Voucher',
        on_delete=models.CASCADE,
        related_name="invoice",
        help_text="The Sales Voucher this invoice is linked to."
    )
    invoice_number = models.CharField(
        max_length=50, 
        unique=True,
        db_index=True,
        help_text="Unique invoice number (e.g., INV-2026-0001)"
    )
    invoice_date = models.DateField(
        auto_now_add=True,
        help_text="Date when the invoice was generated"
    )
    
    # Customer Snapshot (Preserves historical data even if Ledger changes)
    customer_name = models.CharField(max_length=255)
    customer_gstin = models.CharField(
        max_length=15, 
        null=True, 
        blank=True,
        help_text="GSTIN of the customer"
    )
    billing_address = models.TextField(
        blank=True,
        help_text="Billing address of the customer at time of sale"
    )
    
    # Financial Totals
    total_amount = models.DecimalField(
        max_digits=20, 
        decimal_places=2,
        help_text="Base taxable amount (excluding GST)"
    )
    total_tax = models.DecimalField(
        max_digits=20, 
        decimal_places=2,
        help_text="Aggregated GST amount"
    )
    grand_total = models.DecimalField(
        max_digits=20, 
        decimal_places=2,
        help_text="Final invoice value (Base + Tax)"
    )

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        ordering = ['-invoice_date', '-invoice_number']

    def __str__(self):
        return f"{self.invoice_number} | {self.customer_name}"

    @classmethod
    def generate_next_number(cls, company):
        """
        Generates a unique sequential invoice number in the format: INV-YYYY-XXXX.
        """
        year = timezone.now().year
        prefix = f"INV-{year}"
        
        with transaction.atomic():
            # Filter all_objects to include soft-deleted for uniqueness
            count = cls.all_objects.filter(
                company=company,
                invoice_number__startswith=prefix
            ).count()
            
            return f"{prefix}-{str(count + 1).zfill(4)}"
