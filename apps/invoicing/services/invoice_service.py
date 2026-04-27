from decimal import Decimal
from django.db import transaction, models
from invoicing.models import Invoice
from taxation.models import VoucherTax
from voucher.models import VoucherType, EntryType


from django.core.exceptions import ValidationError

def generate_invoice_from_voucher(voucher):
    """
    Business logic to generate a legal Invoice record from a Sales Voucher.
    Ensures data consistency between accounting (Voucher) and taxation (VoucherTax).
    """
    
    # 1. Validation: Only Sales Vouchers can generate Invoices
    if voucher.voucher_type != VoucherType.SALES:
        raise ValueError(f"Invoices can only be generated from Sales Vouchers (Current: {voucher.voucher_type})")

    # 2. Validation: Only APPROVED Vouchers can generate Invoices
    # Note: We check for 'APPROVED' string to avoid tight coupling with choices if not imported
    if hasattr(voucher, 'status') and voucher.status != "APPROVED":
        raise ValidationError(f"Cannot generate invoice. Voucher {voucher.number} is currently in {voucher.status} status and requires approval.")

    # 2. Retrieve Tax Data
    tax_record = VoucherTax.objects.filter(voucher=voucher).first()
    total_tax = tax_record.total_tax if tax_record else Decimal('0.00')

    # 3. Retrieve Party (Customer) Details
    # We identify the party by looking for the Debit entry in a Sales Voucher
    party_entry = voucher.entries.filter(entry_type=EntryType.DEBIT).first()
    if not party_entry:
        # Fallback to any entry if no DR found (unlikely for valid vouchers)
        party_entry = voucher.entries.first()

    if not party_entry:
        raise ValueError(f"Voucher {voucher.number} has no entries. Cannot generate invoice.")

    customer_ledger = party_entry.ledger
    
    # 4. Calculate Financials
    # Grand Total is the amount on the Party (Debit) side
    grand_total = party_entry.amount
    
    # Total Amount (Base taxable value) is Grand Total minus aggregated tax
    total_amount = grand_total - total_tax

    # 5. Idempotent Invoice Creation
    with transaction.atomic():
        invoice, created = Invoice.objects.get_or_create(
            voucher=voucher,
            company=voucher.company,
            defaults={
                "invoice_number": Invoice.generate_next_number(voucher.company),
                "customer_name": customer_ledger.name,
                "customer_gstin": customer_ledger.gstin,
                "billing_address": customer_ledger.address or "",
                "total_amount": total_amount,
                "total_tax": total_tax,
                "grand_total": grand_total,
                "created_by": voucher.created_by,
                "updated_by": voucher.created_by,
            }
        )
        
        return invoice
