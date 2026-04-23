"""Debug: Check Voucher Entries and Trial Balance."""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from company.models import Company
from voucher.models import Voucher, VoucherEntry
from ledger.models import Ledger
from reports.services import generate_trial_balance, generate_profit_and_loss
from django.db.models import Sum

company = Company.objects.first()
print(f"Company: {company.name}")

vouchers = Voucher.objects.filter(company=company)
print(f"Total Vouchers: {vouchers.count()}")
for v in vouchers:
    print(f"- {v.number}: Type={v.voucher_type}, Posted={v.is_posted}, Entries={v.entries.count()}")
    for e in v.entries.all():
        print(f"  * {e.entry_type}: {e.ledger.name} -> {e.amount}")

entries_agg = VoucherEntry.objects.filter(
    ledger__company=company
).values('ledger_id', 'entry_type').annotate(total=Sum('amount'))

print("\nAggregated Entries:")
for agg in entries_agg:
    ledger = Ledger.objects.get(id=agg['ledger_id'])
    print(f"- {ledger.name} ({agg['entry_type']}): {agg['total']}")

print("\nTrial Balance:")
tb = generate_trial_balance(company)
print(f"Balanced: {tb['is_balanced']}")
print(f"Total Debit: {tb['total_debit']}")
print(f"Total Credit: {tb['total_credit']}")

for category, items in tb['data'].items():
    print(f"\n{category}:")
    for item in items:
        if item['debit'] > 0 or item['credit'] > 0:
            print(f"  {item['name']}: DR={item['debit']} CR={item['credit']}")

print("\nProfit and Loss:")
pl = generate_profit_and_loss(company)
print(f"Total Income: {pl['total_income']}")
print(f"Total Expenses: {pl['total_expenses']}")
print(f"Net Result: {pl['net_result']} ({'Profit' if pl['is_profit'] else 'Loss'})")
