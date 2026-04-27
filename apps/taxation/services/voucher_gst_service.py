from decimal import Decimal
from django.db import transaction
from taxation.models import GSTProfile, VoucherTax
from taxation.services.gst_service import calculate_gst


def apply_gst_to_voucher(voucher):
    """
    Scans a voucher's entries for GST applicability and stores a tax breakdown.
    This is called after a voucher and its entries are saved.
    """
    # 1. Check if any entry has GST applicable
    entries_with_gst = voucher.entries.filter(gst_applicable=True)
    if not entries_with_gst.exists():
        # Clean up any existing tax details if no longer applicable
        VoucherTax.objects.filter(voucher=voucher).delete()
        return None

    # 2. Get Company GST Profile for the seller's state
    gst_profile = GSTProfile.objects.filter(company=voucher.company).first()
    if not gst_profile:
        # Cannot calculate GST without a company profile
        return None

    seller_state_code = gst_profile.state_code
    
    total_cgst = Decimal('0.00')
    total_sgst = Decimal('0.00')
    total_igst = Decimal('0.00')
    total_tax_sum = Decimal('0.00')

    # 3. Identify the "Party" state code
    # We look for a ledger in the voucher that has a GSTIN
    party_entry = voucher.entries.filter(ledger__gstin__isnull=False).exclude(gst_applicable=True).first()
    
    if party_entry and party_entry.ledger.gstin and len(party_entry.ledger.gstin) >= 2:
        buyer_state_code = party_entry.ledger.gstin[:2]
    else:
        # Fallback to seller's state (Intra-state) if no party found
        buyer_state_code = seller_state_code

    # 4. Calculate GST for each applicable entry
    for entry in entries_with_gst:
        if not entry.tax_rate:
            continue
            
        calc = calculate_gst(
            amount=entry.amount,
            seller_state_code=seller_state_code,
            buyer_state_code=buyer_state_code,
            tax_rate=entry.tax_rate
        )
        
        total_cgst += Decimal(str(calc['cgst_amount']))
        total_sgst += Decimal(str(calc['sgst_amount']))
        total_igst += Decimal(str(calc['igst_amount']))
        total_tax_sum += Decimal(str(calc['total_tax']))

    # 5. Atomic Update/Create of VoucherTax
    with transaction.atomic():
        VoucherTax.objects.filter(voucher=voucher).delete()
        
        return VoucherTax.objects.create(
            voucher=voucher,
            cgst_amount=total_cgst,
            sgst_amount=total_sgst,
            igst_amount=total_igst,
            total_tax=total_tax_sum
        )
