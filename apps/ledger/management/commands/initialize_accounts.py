from django.core.management.base import BaseCommand
from company.models import Company
from ledger.models import LedgerGroup
from django.db import transaction

class Command(BaseCommand):
    help = 'Initializes the standard Tally Chart of Accounts (28 groups) for a company.'

    def add_arguments(self, parser):
        parser.add_argument('--company_id', type=int, help='Specific company ID to initialize')

    def handle(self, *args, **options):
        company_id = options.get('company_id')
        if company_id:
            companies = Company.objects.filter(id=company_id)
        else:
            companies = Company.objects.all()

        if not companies.exists():
            self.stdout.write(self.style.ERROR('No companies found.'))
            return

        for company in companies:
            self.stdout.write(f"Initializing Tally groups for {company.name}...")
            self.initialize_tally_groups(company)
            self.stdout.write(self.style.SUCCESS(f"Successfully initialized groups for {company.name}"))

    def initialize_tally_groups(self, company):
        # Tally Hierarchy: [Group Name, Parent Name (None for Primary)]
        tally_hierarchy = [
            # Primary Groups
            ('Assets', None),
            ('Liabilities', None),
            ('Income', None),
            ('Expenses', None),

            # Secondary Groups under Assets
            ('Current Assets', 'Assets'),
            ('Fixed Assets', 'Assets'),
            ('Investments', 'Assets'),
            ('Loans & Advances (Asset)', 'Assets'),
            ('Stock-in-hand', 'Current Assets'),
            ('Cash-in-hand', 'Current Assets'),
            ('Bank Accounts', 'Current Assets'),
            ('Sundry Debtors', 'Current Assets'), # Parties - Customers

            # Secondary Groups under Liabilities
            ('Current Liabilities', 'Liabilities'),
            ('Loans (Liability)', 'Liabilities'),
            ('Capital Account', 'Liabilities'),
            ('Reserves & Surplus', 'Liabilities'),
            ('Sundry Creditors', 'Current Liabilities'), # Parties - Suppliers
            ('Duties & Taxes', 'Current Liabilities'),   # GST / TDS
            ('Provisions', 'Current Liabilities'),

            # Secondary Groups under Income
            ('Sales Accounts', 'Income'),
            ('Direct Incomes', 'Income'),
            ('Indirect Incomes', 'Income'),

            # Secondary Groups under Expenses
            ('Purchase Accounts', 'Expenses'),
            ('Direct Expenses', 'Expenses'),
            ('Indirect Expenses', 'Expenses'),
        ]

        # Indian Taxation specialized groups (Subgroups of Duties & Taxes)
        tax_hierarchy = [
            ('GST', 'Duties & Taxes'),
            ('TDS', 'Duties & Taxes'),
            ('CGST', 'GST'),
            ('SGST', 'GST'),
            ('IGST', 'GST'),
        ]

        full_hierarchy = tally_hierarchy + tax_hierarchy

        with transaction.atomic():
            created_groups = {}
            
            for group_name, parent_name in full_hierarchy:
                parent = None
                if parent_name:
                    parent = created_groups.get(parent_name)
                    if not parent:
                        # Try to get from DB if not in current run cache
                        parent = LedgerGroup.objects.filter(company=company, name=parent_name).first()

                group, created = LedgerGroup.objects.get_or_create(
                    company=company,
                    name=group_name,
                    defaults={'parent': parent}
                )
                created_groups[group_name] = group
                
                if created:
                    self.stdout.write(f"  + Created group: {group_name}")
                else:
                    # Update parent if it was None but now we have it
                    if parent and group.parent != parent:
                        group.parent = parent
                        group.save()
