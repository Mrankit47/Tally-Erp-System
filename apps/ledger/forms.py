from django import forms
from .models import Ledger, LedgerGroup

class LedgerForm(forms.ModelForm):
    """
    Form for creating and updating Ledgers.
    """
    class Meta:
        model = Ledger
        fields = ['name', 'group', 'opening_balance']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'placeholder': 'e.g. HDFC Bank Account'
            }),
            'group': forms.Select(attrs={
                'class': 'block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'opening_balance': forms.NumberInput(attrs={
                'class': 'block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'step': '0.01'
            }),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            # Only show groups belonging to this company
            self.fields['group'].queryset = LedgerGroup.objects.filter(company=company)
