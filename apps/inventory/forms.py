from django import forms
from .models import StockItem

class StockItemForm(forms.ModelForm):
    """
    Form for creating and editing Stock Items (Inventory Masters).
    Designed to be fully compatible with Tailwind CSS styling.
    """
    class Meta:
        model = StockItem
        fields = ['name', 'unit_of_measure', 'opening_stock_qty']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'block w-full rounded-xl border-gray-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm transition-colors',
                'placeholder': 'e.g., Apple MacBook Pro 14"'
            }),
            'unit_of_measure': forms.TextInput(attrs={
                'class': 'block w-full rounded-xl border-gray-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm transition-colors',
                'placeholder': 'Nos, Pcs, Kgs...'
            }),
            'opening_stock_qty': forms.NumberInput(attrs={
                'class': 'block w-full rounded-xl border-gray-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 sm:text-sm transition-colors',
                'placeholder': '0.00',
                'step': '0.01'
            }),
        }

    def clean_opening_stock_qty(self):
        qty = self.cleaned_data.get('opening_stock_qty')
        if qty < 0:
            raise forms.ValidationError("Opening stock cannot be negative.")
        return qty
