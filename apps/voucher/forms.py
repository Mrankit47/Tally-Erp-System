from django import forms
from .models import Voucher, VoucherEntry, EntryType
from ledger.models import Ledger
from inventory.models import StockItem

class VoucherHeaderForm(forms.ModelForm):
    """Form for the Voucher header data."""
    class Meta:
        model = Voucher
        fields = ['date', 'narration']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'block w-full rounded-lg border-gray-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm'
            }),
            'narration': forms.Textarea(attrs={
                'rows': 2,
                'class': 'block w-full rounded-lg border-gray-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm',
                'placeholder': 'Explain the transaction...'
            }),
        }

class VoucherEntryForm(forms.ModelForm):
    """Form for a single line item in a voucher."""
    class Meta:
        model = VoucherEntry
        fields = ['ledger', 'amount', 'entry_type', 'stock_item', 'quantity', 'rate']
        widgets = {
            'ledger': forms.Select(attrs={
                'class': 'block w-full rounded-lg border-gray-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'block w-full rounded-lg border-gray-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm',
                'placeholder': '0.00',
                'step': '0.01'
            }),
            'entry_type': forms.Select(attrs={
                'class': 'block w-full rounded-lg border-gray-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm'
            }),
            'stock_item': forms.Select(attrs={
                'class': 'block w-full rounded-lg border-gray-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'block w-full rounded-lg border-gray-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm',
                'placeholder': 'Qty'
            }),
            'rate': forms.NumberInput(attrs={
                'class': 'block w-full rounded-lg border-gray-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm',
                'placeholder': 'Rate'
            }),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['ledger'].queryset = Ledger.objects.filter(company=company)
            self.fields['stock_item'].queryset = StockItem.objects.filter(company=company)

# Custom FormSet for entries to handle cross-row validation
class BaseVoucherEntryFormSet(forms.BaseInlineFormSet):
    def clean(self):
        """Checks if Dr == Cr."""
        super().clean()
        
        if any(self.errors):
            return

        dr_total = 0
        cr_total = 0
        count = 0

        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            
            data = form.cleaned_data
            if data and not data.get('DELETE', False):
                amount = data.get('amount', 0)
                if data.get('entry_type') == EntryType.DEBIT:
                    dr_total += amount
                else:
                    cr_total += amount
                count += 1

        if count < 2:
            raise forms.ValidationError("At least two entries are required for a balanced transaction.")

        if dr_total != cr_total:
            raise forms.ValidationError(
                f"Accounting Mismatch: Total Debit ({dr_total}) must equal Total Credit ({cr_total})."
            )

VoucherEntryFormSet = forms.inlineformset_factory(
    Voucher,
    VoucherEntry,
    form=VoucherEntryForm,
    formset=BaseVoucherEntryFormSet,
    extra=2, # Default to 2 rows (standard entry)
    can_delete=False
)
