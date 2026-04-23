"""Force re-sync ledgers for The Virtual Canvas after parser fix."""
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

print(f"Re-syncing ledgers for: {company.name}")
service = TallySyncService(company, user)

try:
    count = service.sync_ledgers_from_tally()
    print(f"SUCCESS: Synced {count} ledgers")
except Exception as e:
    import traceback
    traceback.print_exc()

# Verify
print("\n=== Verifying DB Values ===")
from ledger.models import Ledger
for l in Ledger.objects.filter(company=company).select_related('group'):
    print(f"  {l.name}")
    print(f"    Group: {l.group.name if l.group else 'NONE'}")
