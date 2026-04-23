"""Force re-sync stock items for The Virtual Canvas after parser fix."""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))
django.setup()

from company.models import Company
from django.contrib.auth import get_user_model
from tally_integration.services import TallySyncService

User = get_user_model()
user = User.objects.first()
company = Company.objects.get(name="The Virtual Canvas")

print(f"Re-syncing stock items for: {company.name}")
service = TallySyncService(company, user)

try:
    count = service.sync_stock_items_from_tally()
    print(f"SUCCESS: Synced {count} items")
except Exception as e:
    import traceback
    traceback.print_exc()

# Verify
print("\n=== Verifying DB Values ===")
from inventory.models import StockItem
for si in StockItem.objects.filter(company=company).select_related('group'):
    print(f"  {si.name}")
    print(f"    Group: {si.group.name if si.group else 'NONE'}")
    print(f"    Opening: {si.opening_stock_qty} | Closing: {si.closing_stock_qty}")
    print(f"    Current: {si.current_quantity}")
