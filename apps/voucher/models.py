"""
Voucher models.

The heart of the accounting system. 
Handles financial transactions, ensuring double-entry integrity
and sequential document numbering.
"""

from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from core.models import TenantModel
from company.models import Company



class VoucherType(models.TextChoices):
    """Supported transaction types in the ERP."""
    CONTRA = 'CONTRA', 'Contra'
    PAYMENT = 'PAYMENT', 'Payment'
    RECEIPT = 'RECEIPT', 'Receipt'
    JOURNAL = 'JOURNAL', 'Journal'
    SALES = 'SALES', 'Sales'
    PURCHASE = 'PURCHASE', 'Purchase'


class VoucherStatus(models.TextChoices):
    """Workflow states for a voucher."""
    DRAFT = 'DRAFT', 'Draft'
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'


class EntryType(models.TextChoices):
    """Debit or Credit indicator."""
    DEBIT = 'DR', 'Debit'
    CREDIT = 'CR', 'Credit'


class CustomVoucherType(TenantModel):
    """
    User-defined Voucher Types (e.g., 'Export Sales', 'Bank Receipt').
    Inherits behavioral logic from the base VoucherType.
    """
    name = models.CharField(max_length=255)
    parent_type = models.CharField(
        max_length=20,
        choices=VoucherType.choices,
        help_text='Base system behavior to inherit (e.g., SALES, PURCHASE).'
    )
    is_active = models.BooleanField(default=True)
    method_of_numbering = models.CharField(
        max_length=50,
        choices=[
            ('Automatic', 'Automatic'),
            ('Manual', 'Manual'),
            ('None', 'None')
        ],
        default='Automatic'
    )

    class Meta:
        verbose_name = 'Custom Voucher Type'
        verbose_name_plural = 'Custom Voucher Types'
        unique_together = ['company', 'name']
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (Parent: {self.get_parent_type_display()})"


class VoucherSequence(models.Model):
    """
    Internal tracker for the next available voucher number.
    Scoped to Company + VoucherType.
    """
    objects = models.Manager()
    company = models.ForeignKey('company.Company', on_delete=models.CASCADE)
    voucher_type = models.CharField(max_length=20, choices=VoucherType.choices)

    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ['company', 'voucher_type']


class Voucher(TenantModel):
    """
    Financial document header.
    """
    number = models.CharField(
        max_length=50,
        editable=False,
        help_text='Auto-generated voucher number (e.g., SAL-0001).'
    )
    date = models.DateField(
        default=timezone.now,
        db_index=True
    )
    voucher_type = models.CharField(
        max_length=20,
        choices=VoucherType.choices,
        db_index=True
    )
    custom_voucher_type = models.ForeignKey(
        CustomVoucherType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vouchers',
        help_text='Optional link to a user-defined custom voucher type.'
    )
    narration = models.TextField(
        blank=True,
        help_text='General comments for this transaction.'
    )
    party_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Name of the associated party (Customer, Vendor, etc.)'
    )
    is_posted = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Once posted, the voucher and its entries become read-only.'
    )
    status = models.CharField(
        max_length=10,
        choices=VoucherStatus.choices,
        default=VoucherStatus.APPROVED,
        db_index=True,
        help_text='Workflow status (Draft, Pending, Approved)'
    )

    class Meta:
        verbose_name = 'Voucher'
        verbose_name_plural = 'Vouchers'
        ordering = ['-date', '-number']
        indexes = [
            models.Index(fields=['company', 'date', 'voucher_type']),
        ]

    def __str__(self):
        return f"{self.number} | {self.date}"

    def clean(self):
        """
        Enforce business rules:
        1. Date must be within the company's financial year.
        2. Prevent modification if is_posted is True.
        3. (On update) Ensure total DR equals total CR.
        """
        # Block edits to posted vouchers
        if not self._state.adding:
            original = Voucher.all_objects.get(pk=self.pk)
            if original.is_posted:
                # Allow unposting only if specifically implemented, 
                # but here we block all attribute changes if originally posted.
                raise ValidationError("Cannot modify a posted voucher. Unpost it first if permitted.")

        # 1. Financial Year Check
        company: Company = self.company  # type: ignore
        if self.date < company.financial_year_start or self.date > company.financial_year_end:
            raise ValidationError(
                f"Voucher date {self.date} must be within the financial year "
                f"({company.financial_year_start} to {company.financial_year_end})."
            )

        # 2. Double-Entry Balance Check
        # A voucher must always be balanced (Dr = Cr) if it is marked as posted.
        if self.is_posted and self.pk:
            from django.db.models import Sum
            entries = self.entries.all()  # type: ignore
            if not entries.exists():
                raise ValidationError("Cannot post an empty voucher. At least two entries are required.")
                
            dr_sum = entries.filter(entry_type=EntryType.DEBIT).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
            cr_sum = entries.filter(entry_type=EntryType.CREDIT).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
            
            if dr_sum != cr_sum:
                raise ValidationError(
                    f"Accounting Mismatch: Total Debit ({dr_sum}) must equal Total Credit ({cr_sum}) for posted vouchers."
                )

    def delete(self, using=None, keep_parents=False):
        """Block deletion of posted vouchers."""
        if self.is_posted:
            raise ValidationError("Cannot delete a posted voucher.")
        return super().delete(using=using, keep_parents=keep_parents)

    def save(self, *args, **kwargs):
        """
        Handle auto-numbering on first save.
        """
        if not self.number:
            with transaction.atomic():  # type: ignore
                seq, _ = VoucherSequence.objects.select_for_update().get_or_create(
                    company=self.company,
                    voucher_type=self.voucher_type
                )
                seq.last_number += 1
                seq.save()
                
                prefix = self.voucher_type[:3].upper()  # type: ignore
                self.number = f"{prefix}-{str(seq.last_number).zfill(4)}"  # type: ignore
        
        super().save(*args, **kwargs)


class VoucherEntry(TenantModel):
    """
    Individual line items within a voucher.
    Each entry represents a single movement in a Ledger.
    """
    voucher = models.ForeignKey(
        Voucher,
        on_delete=models.CASCADE,
        related_name='entries'
    )
    ledger = models.ForeignKey(
        'ledger.Ledger',
        on_delete=models.PROTECT,
        related_name='voucher_entries'
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text='Absolute value of the transaction.'
    )
    entry_type = models.CharField(
        max_length=2,
        choices=EntryType.choices,
        help_text='DR for Debit, CR for Credit.'
    )
    # Inventory Linkage (Optional for non-inventory vouchers)
    stock_item = models.ForeignKey(
        'inventory.StockItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voucher_entries'
    )
    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Quantity for item-based entries.'
    )
    rate = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Rate per unit.'
    )
    
    # GST Extension (Optional)
    gst_applicable = models.BooleanField(
        default=False,
        help_text="Enable GST calculation for this entry"
    )
    hsn_code = models.ForeignKey(
        'taxation.HSNCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voucher_entries'
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="GST percentage applied to this entry"
    )

    class Meta:
        verbose_name = 'Voucher Entry'
        verbose_name_plural = 'Voucher Entries'
        # Ensure positive amounts
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name='voucher_entry_amount_positive'),
        ]
        indexes = [
            models.Index(fields=['company', 'ledger', 'voucher']),
        ]

    def __str__(self):
        return f"{self.voucher.number} | {self.entry_type} {self.ledger.name} {self.amount}"


class AuditRiskResolution(TenantModel):
    """
    Stores resolutions/acknowledgements of programmatic audit risk alerts by Managers/Admins.
    """
    voucher = models.ForeignKey(
        'Voucher',
        on_delete=models.CASCADE,
        related_name='risk_resolutions'
    )
    risk_type = models.CharField(max_length=50) # e.g. 'ANOMALY', 'DUPLICATE', 'COMPLIANCE', 'AUDIT'
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    resolved_at = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Audit Risk Resolution'
        verbose_name_plural = 'Audit Risk Resolutions'
        unique_together = ['company', 'voucher', 'risk_type']

    def __str__(self):
        return f"Resolution for {self.voucher.number} | {self.risk_type}"
