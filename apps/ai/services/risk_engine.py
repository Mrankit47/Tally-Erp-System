import logging
from decimal import Decimal
from datetime import datetime, time
from django.utils import timezone
from django.db.models import Avg, Sum
from voucher.models import Voucher, VoucherEntry, EntryType, VoucherType

logger = logging.getLogger('apps.ai')

def audit_company_vouchers_for_risks(company) -> list:
    """
    Performs algorithmic audit risk detection on vouchers.
    Returns list of risk alert dictionaries.
    """
    alerts = []
    try:
        vouchers = Voucher.objects.filter(company=company)
        if not vouchers.exists():
            return []

        # 1. Flag High-Value Vouchers
        avg_amt_query = VoucherEntry.objects.filter(
            voucher__company=company,
            entry_type=EntryType.DEBIT
        ).aggregate(avg=Avg('amount'))
        avg_amt = avg_amt_query['avg'] or Decimal('5000.00')

        high_val_vouchers = VoucherEntry.objects.filter(
            voucher__company=company,
            entry_type=EntryType.DEBIT,
            amount__gt=avg_amt * Decimal('2.5')
        ).select_related('voucher')[:5]

        for entry in high_val_vouchers:
            alerts.append({
                'id': str(entry.voucher.id),
                'risk_type': 'ANOMALY',
                'title': 'Unusually Large Transaction',
                'description': f"Voucher {entry.voucher.number} is for ₹{entry.amount:,.2f} which exceeds 250% of your historical average of ₹{avg_amt:,.2f}.",
                'severity': 'HIGH',
                'ref': entry.voucher.number
            })

        # 2. Flag Potential Duplicate Vouchers
        # Look for identical dates, total debit sums, and party names
        duplicate_candidates = VoucherEntry.objects.filter(
            voucher__company=company,
            entry_type=EntryType.DEBIT
        ).values('voucher__date', 'amount', 'voucher__party_name').annotate(
            count=Sum('id') # Aggregate query trick to find count
        )

        duplicates = []
        # Find matches by traversing database
        all_entries = VoucherEntry.objects.filter(
            voucher__company=company,
            entry_type=EntryType.DEBIT
        ).select_related('voucher')

        seen = {}
        for entry in all_entries:
            key = (entry.voucher.date, entry.amount, entry.voucher.party_name)
            if key in seen:
                duplicate_v = seen[key]
                if entry.voucher.number != duplicate_v.number:
                    alerts.append({
                        'id': str(entry.voucher.id),
                        'risk_type': 'DUPLICATE',
                        'title': 'Potential Duplicate Voucher',
                        'description': f"Voucher {entry.voucher.number} matches {duplicate_v.number} exactly in Date, Party Name, and Amount (₹{entry.amount:,.2f}). Possible double-billing.",
                        'severity': 'HIGH',
                        'ref': entry.voucher.number
                    })
            else:
                seen[key] = entry.voucher

        # 3. Flag Vouchers Recorded in Off-Hours (e.g. before 8 AM or after 9 PM)
        off_hours_vouchers = Voucher.objects.filter(company=company)
        for v in off_hours_vouchers:
            created_at = getattr(v, 'created_at', None) or getattr(v, 'updated_at', None)
            if created_at:
                # Convert timezone aware datetime to local time
                local_time = timezone.localtime(created_at).time()
                if local_time < time(8, 0) or local_time > time(21, 0):
                    alerts.append({
                        'id': str(v.id),
                        'risk_type': 'COMPLIANCE',
                        'title': 'Off-Hours Transaction Logging',
                        'description': f"Voucher {v.number} was entered or altered at {local_time.strftime('%I:%M %p')}, which is outside standard business corporate hours.",
                        'severity': 'MEDIUM',
                        'ref': v.number
                    })

        # 4. Flag Vouchers with Missing or Empty Narrations
        empty_narrations = Voucher.objects.filter(company=company, narration__isnull=True) | \
                           Voucher.objects.filter(company=company, narration="")
        for v in empty_narrations:
            alerts.append({
                'id': str(v.id),
                'risk_type': 'AUDIT',
                'title': 'Empty Bookkeeping Narration',
                'description': f"Voucher {v.number} is missing its standard explanatory ledger narration. This may violate internal auditing guidelines.",
                'severity': 'LOW',
                'ref': v.number
            })

        logger.info(f"Programmatic audit scanning completed. Flagged {len(alerts)} items.")
        return alerts

    except Exception as e:
        logger.error(f"Error executing voucher risk auditing: {e}", exc_info=True)
        return []
