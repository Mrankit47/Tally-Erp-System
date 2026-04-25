"""
Voucher Services.

Encapsulates business logic for voucher operations, ensuring
transactional integrity and strict accounting rules.
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Voucher, VoucherEntry, EntryType


def create_voucher_with_entries(company, user, voucher_type, date, narration, entries_data):
    """
    Atomically creates a Voucher and its associated VoucherEntry records.

    Args:
        company: The Company the voucher belongs to.
        user: The User creating the voucher.
        voucher_type: One of VoucherType choices.
        date: Voucher date.
        narration: Comments.
        entries_data: List of dicts like {'ledger': Ledger, 'amount': Decimal, 'type': 'DR'/'CR'}

    Returns:
        The created Voucher object.

    Raises:
        ValidationError: If Dr != Cr or other accounting rules fail.
    """
    
    # 1. Pre-validation: Total Dr must equal Total Cr
    dr_total = Decimal('0.00')
    cr_total = Decimal('0.00')
    
    for entry in entries_data:
        amount = Decimal(str(entry['amount']))
        if entry['type'] == EntryType.DEBIT:
            dr_total += amount
        else:
            cr_total += amount
            
    if dr_total != cr_total:
        raise ValidationError(
            f"Accounting Mismatch: Total Debit ({dr_total}) != Total Credit ({cr_total})."
        )
        
    if not entries_data:
        raise ValidationError("A voucher must have at least two entries.")

    with transaction.atomic():
        # 2. Create Voucher Header
        voucher = Voucher.objects.create(
            company=company,
            created_by=user,
            updated_by=user,
            voucher_type=voucher_type,
            date=date,
            narration=narration
        )
        
        # 3. Create Entries
        for entry in entries_data:
            VoucherEntry.objects.create(
                company=company,
                created_by=user,
                updated_by=user,
                voucher=voucher,
                ledger=entry['ledger'],
                amount=entry['amount'],
                entry_type=entry['type']
            )
            
        # 4. Final verification (triggers model clean())
        voucher.full_clean()
        
    # 5. Apply GST if applicable (Safe Extension)
    try:
        from taxation.services.voucher_gst_service import apply_gst_to_voucher
        apply_gst_to_voucher(voucher)
    except ImportError:
        # If taxation app is not installed or service is missing, fail silently
        pass
        
    return voucher
