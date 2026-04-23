"""Check LedgerGroup hierarchy for The Virtual Canvas."""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))
django.setup()

from company.models import Company
from ledger.models import LedgerGroup, Ledger
from reports.services import get_ledger_category

company = Company.objects.get(name="The Virtual Canvas")
print(f"=== Ledger Groups for: {company.name} ===")
groups = LedgerGroup.objects.filter(company=company)
group_map = {g.id: g for g in groups}

for g in groups:
    parent_name = g.parent.name if g.parent else "None"
    print(f"Group: {g.name} | Parent: {parent_name}")

print("\n=== Ledgers and their root categories ===")

ledgers = Ledger.objects.filter(company=company).select_related('group')
for l in ledgers:
    category = get_ledger_category(l.group, group_map)
    print(f"Ledger: {l.name} | Group: {l.group.name} | Category: {category}")
