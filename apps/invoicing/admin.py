from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """
    Admin interface for Invoice management.
    """
    list_display = (
        'invoice_number', 
        'customer_name', 
        'grand_total', 
        'invoice_date', 
        'company'
    )
    
    list_filter = ('company', 'invoice_date')
    search_fields = (
        'invoice_number', 
        'customer_name', 
        'customer_gstin'
    )
    readonly_fields = (
        'invoice_number', 
        'invoice_date', 
        'total_amount', 
        'total_tax', 
        'grand_total',
        'created_at',
        'updated_at'
    )
    
    fieldsets = (
        ('Document Info', {
            'fields': ('company', 'voucher', 'invoice_number', 'invoice_date')
        }),
        ('Customer Details', {
            'fields': ('customer_name', 'customer_gstin', 'billing_address')
        }),
        ('Financial Summary', {
            'fields': ('total_amount', 'total_tax', 'grand_total')
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Invoices should typically be generated via service layer/vouchers,
        # but we allow admin creation for flexibility unless specified otherwise.
        return True
