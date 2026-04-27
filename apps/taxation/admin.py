from django.contrib import admin
from .models import GSTProfile, HSNCode, TaxRate, LedgerTaxMapping


@admin.register(GSTProfile)
class GSTProfileAdmin(admin.ModelAdmin):
    list_display = ('company', 'gstin', 'state', 'state_code', 'is_composition', 'created_at')
    list_filter = ('state', 'is_composition', 'company')
    search_fields = ('gstin', 'company__name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Company Info', {
            'fields': ('company', 'gstin')
        }),
        ('Location Details', {
            'fields': ('state', 'state_code')
        }),
        ('Scheme Details', {
            'fields': ('is_composition',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at', 'is_active'),
            'classes': ('collapse',)
        }),
    )


@admin.register(HSNCode)
class HSNCodeAdmin(admin.ModelAdmin):
    list_display = ('company', 'code', 'description', 'tax_rate', 'is_active')
    list_filter = ('is_active', 'company')
    search_fields = ('code', 'description')
    fieldsets = (
        ('HSN Info', {
            'fields': ('company', 'code', 'description', 'tax_rate')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    list_display = ('company', 'name', 'percentage')
    list_filter = ('name', 'company')
    search_fields = ('company__name', 'name')


@admin.register(LedgerTaxMapping)
class LedgerTaxMappingAdmin(admin.ModelAdmin):
    list_display = ('ledger', 'hsn_code', 'tax_rate', 'is_gst_applicable', 'company')
    list_filter = ('is_gst_applicable', 'company', 'tax_rate')
    search_fields = ('ledger__name', 'hsn_code__code', 'company__name')
    autocomplete_fields = ['ledger', 'hsn_code']


# If Ledger and HSNCode don't have search_fields, autocomplete won't work.
# I'll check if I need to add search_fields to LedgerAdmin if it exists.
