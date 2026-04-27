from django.core.exceptions import ValidationError
from ..models import VoucherStatus

def approve_voucher(voucher, user):
    """
    Business logic to approve a voucher.
    1. Validates current status.
    2. Updates status to APPROVED.
    3. Marks as posted (immutable).
    """
    if voucher.status == VoucherStatus.APPROVED:
        raise ValidationError("Voucher is already approved.")
    
    # Update status and lock the record
    voucher.status = VoucherStatus.APPROVED
    voucher.is_posted = True
    voucher.save()
    
    return voucher
