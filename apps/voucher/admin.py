from django.contrib import admin
from .models import CustomVoucherType, Voucher, VoucherEntry, VoucherSequence

@admin.register(CustomVoucherType)
class CustomVoucherTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'parent_type', 'is_active', 'method_of_numbering')
    list_filter = ('company', 'parent_type', 'is_active')
    search_fields = ('name',)

from taxation.models import VoucherTax

class VoucherTaxInline(admin.TabularInline):
    model = VoucherTax
    extra = 0
    readonly_fields = ('cgst_amount', 'sgst_amount', 'igst_amount', 'total_tax', 'created_at')
    can_delete = False
    verbose_name = "GST Calculation Summary"

class VoucherEntryInline(admin.TabularInline):
    model = VoucherEntry
    extra = 1
    fields = ('ledger', 'entry_type', 'amount', 'gst_applicable', 'hsn_code', 'tax_rate')
    autocomplete_fields = ['ledger', 'hsn_code']

@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = ('number', 'company', 'date', 'voucher_type', 'party_name', 'is_posted')
    list_filter = ('company', 'voucher_type', 'is_posted', 'date')
    search_fields = ('number', 'party_name')
    inlines = [VoucherEntryInline, VoucherTaxInline]

@admin.register(VoucherSequence)
class VoucherSequenceAdmin(admin.ModelAdmin):
    list_display = ('company', 'voucher_type', 'last_number')
    list_filter = ('company', 'voucher_type')
