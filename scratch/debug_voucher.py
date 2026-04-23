"""Debug script to inspect SAL-0002 voucher and the XML being generated."""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from voucher.models import Voucher, VoucherEntry, EntryType
from tally_integration.xml_utilities import TallyXMLGenerator
from inventory.models import StockTransaction

v = Voucher.objects.filter(number='SAL-0002').first()
if not v:
    print("ERROR: Voucher SAL-0002 not found!")
    sys.exit(1)

print(f"=== Voucher: {v.number} ===")
print(f"Date: {v.date}")
print(f"Type: {v.voucher_type}")
print(f"Company: {v.company}")
print(f"Party: {v.party_name}")
print(f"Narration: {v.narration}")
print(f"Sync Status: {v.sync_status}")
print(f"Tally ID: {v.tally_id}")
print()

entries = v.entries.all().select_related('ledger', 'ledger__group', 'stock_item')
print(f"=== Entries ({entries.count()}) ===")
for e in entries:
    group_name = e.ledger.group.name if e.ledger.group else "NO GROUP"
    stock_name = e.stock_item.name if e.stock_item else "None"
    print(f"  {e.entry_type} | Ledger: {e.ledger.name} (Group: {group_name}) | Amount: {e.amount} | Stock: {stock_name} | Qty: {e.quantity} | Rate: {e.rate}")
    
    # Check stock transactions
    stock_txs = StockTransaction.objects.filter(voucher_entry=e)
    for tx in stock_txs:
        print(f"    -> StockTx: {tx.stock_item.name} | Qty: {tx.quantity} | Rate: {tx.rate} | Type: {tx.transaction_type}")

print()
print("=== Generated XML ===")
gen = TallyXMLGenerator()
xml = gen.get_sales_voucher_xml(v)
print(xml)
