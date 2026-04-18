"""
URL configuration for ERP project.

API endpoints are namespaced under /api/v1/ for versioning.
Dashboard UI endpoints are at the root level.
"""

from django.contrib import admin
from django.urls import path, include, reverse
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from core.views import (
    dashboard_view, 
    sync_logs_view, 
    trigger_sync_view, 
    retry_sync_log_view, 
    about_project_view
)


# =============================================================================
# API Root View — lists all available endpoint groups
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """
    ERP API v1 — Root endpoint.

    Lists all available resource groups in the API.
    Authenticate at /api-auth/login/ to access protected endpoints.
    """
    return Response({
        'accounts': request.build_absolute_uri('accounts/'),
        'company':  request.build_absolute_uri('company/'),
        'ledger':   request.build_absolute_uri('ledger/'),
        'voucher':  request.build_absolute_uri('voucher/'),
        'inventory': request.build_absolute_uri('inventory/'),
        'reports':  request.build_absolute_uri('reports/'),
        'tally':    request.build_absolute_uri('tally/'),
        'admin':    request.build_absolute_uri('/admin/'),
    })


# =============================================================================
# API v1 URL Patterns (versioned)
# =============================================================================

api_v1_patterns = [
    path('', api_root, name='api-root'),          # /api/v1/
    path('accounts/', include('accounts.urls')),
    path('company/', include('company.urls')),
    path('ledger/', include('ledger.urls')),
    path('voucher/', include('voucher.urls')),
    path('inventory/', include('inventory.urls')),
    path('reports/', include('reports.urls')),
    path('tally/', include('tally_integration.urls')),
]

# =============================================================================
# Root URL Patterns
# =============================================================================

urlpatterns = [
    # ─── Dashboard UI ───
    path('', dashboard_view, name='dashboard'),
    path('sync-logs/', sync_logs_view, name='sync-logs'),
    path('about-project/', about_project_view, name='about-project'),
    path('reports/', include('reports.urls')),

    # ─── UI AJAX Actions ───
    path('trigger-sync/', trigger_sync_view, name='trigger-sync'),
    path('retry-sync/<int:log_id>/', retry_sync_log_view, name='retry-sync'),

    # ─── Admin ───
    path('admin/', admin.site.urls),

    # ─── API ───
    path('api/v1/', include((api_v1_patterns, 'api-v1'))),

    # DRF browsable API auth (login/logout links)
    path('api-auth/', include('rest_framework.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

