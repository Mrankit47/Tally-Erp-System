from django import forms
from .models import Ledger, LedgerGroup

class LedgerForm(forms.ModelForm):
    """
    Form for creating and updating Ledgers.
    """
    class Meta:
        model = Ledger
        fields = [
            'name', 'alias', 'group', 'opening_balance', 
            'address', 'state', 'country', 'pincode', 
            'pan_no', 'gstin'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'block w-full rounded-2xl border-gray-100 bg-gray-50/50 py-3 px-4 text-sm font-semibold focus:ring-2 focus:ring-brand-500 transition-all',
                'placeholder': 'Ledger Name'
            }),
            'alias': forms.TextInput(attrs={
                'class': 'block w-full rounded-2xl border-gray-100 bg-gray-50/50 py-3 px-4 text-sm font-semibold focus:ring-2 focus:ring-brand-500 transition-all',
                'placeholder': '(alias)'
            }),
            'group': forms.Select(attrs={
                'class': 'block w-full rounded-2xl border-gray-100 bg-gray-50/50 py-3 px-4 text-sm font-semibold focus:ring-2 focus:ring-brand-500 transition-all'
            }),
            'opening_balance': forms.NumberInput(attrs={
                'class': 'block w-full rounded-2xl border-gray-100 bg-gray-50/50 py-3 px-4 text-sm font-semibold focus:ring-2 focus:ring-brand-500 transition-all',
                'step': '0.01'
            }),
            'address': forms.Textarea(attrs={
                'rows': 3,
                'class': 'block w-full rounded-2xl border-gray-100 bg-gray-50/50 py-3 px-4 text-sm font-semibold focus:ring-2 focus:ring-brand-500 transition-all',
                'placeholder': 'Mailing Address'
            }),
            'state': forms.TextInput(attrs={
                'class': 'block w-full rounded-2xl border-gray-100 bg-gray-50/50 py-3 px-4 text-sm font-semibold focus:ring-2 focus:ring-brand-500 transition-all'
            }),
            'country': forms.TextInput(attrs={
                'class': 'block w-full rounded-2xl border-gray-100 bg-gray-50/50 py-3 px-4 text-sm font-semibold focus:ring-2 focus:ring-brand-500 transition-all'
            }),
            'pincode': forms.TextInput(attrs={
                'class': 'block w-full rounded-2xl border-gray-100 bg-gray-50/50 py-3 px-4 text-sm font-semibold focus:ring-2 focus:ring-brand-500 transition-all'
            }),
            'pan_no': forms.TextInput(attrs={
                'class': 'block w-full rounded-2xl border-gray-100 bg-gray-50/50 py-3 px-4 text-sm font-semibold focus:ring-2 focus:ring-brand-500 transition-all'
            }),
            'gstin': forms.TextInput(attrs={
                'class': 'block w-full rounded-2xl border-gray-100 bg-gray-50/50 py-3 px-4 text-sm font-semibold focus:ring-2 focus:ring-brand-500 transition-all'
            }),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            # Only show groups belonging to this company
            self.fields['group'].queryset = LedgerGroup.objects.filter(company=company)
