import logging
from .models import LedgerGroup
from django.db import transaction

logger = logging.getLogger(__name__)

def initialize_tally_groups(company):
    """
    Seeds the standard Tally hierarchy for a company.
    """
    hierarchy = [
        ('Assets', None), ('Liabilities', None), ('Income', None), ('Expenses', None),
        ('Current Assets', 'Assets'), ('Fixed Assets', 'Assets'), ('Investments', 'Assets'),
        ('Loans & Advances (Asset)', 'Assets'), ('Stock-in-hand', 'Current Assets'),
        ('Cash-in-hand', 'Current Assets'), ('Bank Accounts', 'Current Assets'),
        ('Sundry Debtors', 'Current Assets'),
        ('Current Liabilities', 'Liabilities'), ('Loans (Liability)', 'Liabilities'),
        ('Capital Account', 'Liabilities'), ('Reserves & Surplus', 'Liabilities'),
        ('Sundry Creditors', 'Current Liabilities'), ('Duties & Taxes', 'Current Liabilities'),
        ('Provisions', 'Current Liabilities'), ('Sales Accounts', 'Income'),
        ('Direct Incomes', 'Income'), ('Indirect Incomes', 'Income'),
        ('Purchase Accounts', 'Expenses'), ('Direct Expenses', 'Expenses'),
        ('Indirect Expenses', 'Expenses'), ('GST', 'Duties & Taxes'),
        ('TDS', 'Duties & Taxes'), ('CGST', 'GST'), ('SGST', 'GST'), ('IGST', 'GST'),
    ]

    with transaction.atomic():
        created = {}
        for name, parent_name in hierarchy:
            parent = created.get(parent_name)
            group, _ = LedgerGroup.objects.get_or_create(
                company=company,
                name=name,
                defaults={'parent': parent}
            )
            created[name] = group
    return True
