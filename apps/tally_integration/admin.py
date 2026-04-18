"""
Tally Integration Admin.

Provides monitoring and auditing for Tally sync operations.
"""

from django.contrib import admin
from .models import SyncLog


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    """
    Monitoring dashboard for Tally synchronization.
    """
    list_display = (
        'created_at', 
        'operation', 
        'model_name', 
        'status', 
        'records_affected', 
        'company'
    )
    list_filter = ('status', 'operation', 'company', 'created_at')
    search_fields = ('model_name', 'message', 'response_xml')
    readonly_fields = (
        'id', 'created_at', 'updated_at', 'created_by', 
        'updated_by', 'company', 'model_name', 'operation', 
        'status', 'message', 'response_xml', 'records_affected'
    )
    
    def has_add_permission(self, request):
        return False  # Logs are system-generated only

    fieldsets = (
        ('Event Overview', {
            'fields': ('company', 'model_name', 'operation', 'status', 'records_affected')
        }),
        ('Result Details', {
            'fields': ('message', 'response_xml')
        }),
        ('Audit Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
