from django.db import models
from core.models import TenantModel


class GSTProfile(TenantModel):
    """
    Stores GST registration details for a Company/Tenant.
    """
    gstin = models.CharField(
        max_length=15, 
        help_text="GST Identification Number (e.g., 27AAAAA0000A1Z5)"
    )
    state = models.CharField(
        max_length=100, 
        help_text="State name where registered"
    )
    state_code = models.CharField(
        max_length=2, 
        help_text="2-digit GST state code (e.g., 27 for Maharashtra)"
    )
    is_composition = models.BooleanField(
        default=False, 
        help_text="Whether the company is under GST Composition Scheme"
    )

    class Meta:
        verbose_name = "GST Profile"
        verbose_name_plural = "GST Profiles"
        unique_together = ['company', 'gstin']

    def __str__(self):
        return f"{self.gstin} ({self.state})"


class HSNCode(TenantModel):
    """
    HSN (Harmonized System of Nomenclature) or SAC (Services Accounting Code).
    """
    code = models.CharField(
        max_length=20, 
        help_text="HSN or SAC Code"
    )
    description = models.TextField(
        blank=True, 
        help_text="Description of the goods or services"
    )
    tax_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        help_text="Default GST tax rate percentage for this HSN"
    )

    class Meta:
        verbose_name = "HSN Code"
        verbose_name_plural = "HSN Codes"
        unique_together = ['company', 'code']

    def __str__(self):
        return f"{self.code} - {self.description[:30]}" if self.description else self.code


class TaxRate(TenantModel):
    """
    Individual Tax Components (CGST, SGST, IGST).
    """
    class TaxType(models.TextChoices):
        CGST = 'CGST', 'Central GST'
        SGST = 'SGST', 'State GST'
        IGST = 'IGST', 'Integrated GST'

    name = models.CharField(
        max_length=10, 
        choices=TaxType.choices,
        help_text="Type of tax component"
    )
    percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        help_text="Tax percentage rate"
    )

    class Meta:
        verbose_name = "Tax Rate"
        verbose_name_plural = "Tax Rates"
        unique_together = ['company', 'name', 'percentage']

    def __str__(self):
        return f"{self.get_name_display()} @ {self.percentage}%"


class LedgerTaxMapping(TenantModel):
    """
    Maps tax settings to individual ledgers (Sales, Purchases, Items).
    Allows overriding HSN and rates at the ledger level.
    """
    ledger = models.ForeignKey(
        'ledger.Ledger', 
        on_delete=models.CASCADE, 
        related_name='tax_mappings',
        help_text="The ledger this tax setting applies to"
    )
    hsn_code = models.ForeignKey(
        HSNCode, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='ledger_mappings',
        help_text="HSN Code applicable to this ledger"
    )
    tax_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        help_text="Specific GST percentage for this ledger"
    )
    is_gst_applicable = models.BooleanField(
        default=True,
        help_text="Whether GST is applicable for this ledger"
    )

    class Meta:
        verbose_name = "Ledger Tax Mapping"
        verbose_name_plural = "Ledger Tax Mappings"
        unique_together = ['company', 'ledger']

    def __str__(self):
        return f"Tax Mapping: {self.ledger.name} ({self.tax_rate}%)"


class VoucherTax(models.Model):
    """
    Stores the aggregated GST breakdown for a Voucher.
    Linked to the Voucher header.
    """
    voucher = models.ForeignKey(
        'voucher.Voucher', 
        on_delete=models.CASCADE, 
        related_name="tax_details"
    )
    cgst_amount = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=0,
        help_text="Total Central GST amount for this voucher"
    )
    sgst_amount = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=0,
        help_text="Total State GST amount for this voucher"
    )
    igst_amount = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=0,
        help_text="Total Integrated GST amount for this voucher"
    )
    total_tax = models.DecimalField(
        max_digits=20, 
        decimal_places=2,
        help_text="Sum of all GST components"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Voucher Tax Detail"
        verbose_name_plural = "Voucher Tax Details"

    def __str__(self):
        return f"Tax for {self.voucher.number} (Total: {self.total_tax})"
