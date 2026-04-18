from django.core.management.base import BaseCommand
from django.http import QueryDict
from company.models import Company
from voucher.forms import VoucherEntryFormSet
from voucher.models import Voucher, EntryType
from ledger.models import Ledger

class Command(BaseCommand):
    def handle(self, *args, **options):
        company = Company.objects.first()
        ledger = Ledger.objects.first()
        
        data = QueryDict('', mutable=True)
        data.update({
            'entries-TOTAL_FORMS': '2',
            'entries-INITIAL_FORMS': '0',
            'entries-MIN_NUM_FORMS': '0',
            'entries-MAX_NUM_FORMS': '1000',
            'entries-0-ledger': str(ledger.id),
            'entries-0-entry_type': 'DR',
            'entries-0-amount': '5000',
            'entries-0-id': '',
            'entries-1-ledger': str(ledger.id),
            'entries-1-entry_type': 'CR',
            'entries-1-amount': '5000',
            'entries-1-id': '',
        })

        formset = VoucherEntryFormSet(data, instance=Voucher(company=company), form_kwargs={'company': company})
        is_valid = formset.is_valid()
        self.stdout.write(f'is_valid: {is_valid}')
        self.stdout.write(f'errors: {formset.errors}')
        self.stdout.write(f'non_form_errors: {formset.non_form_errors()}')

        for i, form in enumerate(formset.forms):
            self.stdout.write(f'Form {i} data: {getattr(form, "cleaned_data", "No cleaned_data")}')
            self.stdout.write(f'Form {i} has_changed: {form.has_changed()}')
