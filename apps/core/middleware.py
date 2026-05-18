"""
Global error handling middleware.

Catches unhandled exceptions in the request/response cycle,
logs the full traceback, and returns a consistent JSON error response.
This prevents raw 500 pages from leaking implementation details.
"""

import logging
import traceback

from django.http import JsonResponse

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware:
    """
    Middleware that wraps the entire request cycle in a try/except.

    - In DEBUG mode: includes the traceback in the response for easier debugging.
    - In production: returns a generic error message and logs the full traceback.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as exc:
            return self.handle_exception(request, exc)

    def handle_exception(self, request, exc):
        """Log the exception and return a structured JSON error response."""
        tb = traceback.format_exc()

        logger.error(
            'Unhandled exception on %s %s: %s\n%s',
            request.method,
            request.get_full_path(),
            str(exc),
            tb,
        )

        from django.conf import settings

        response_data = {
            'success': False,
            'error': {
                'message': 'An internal server error occurred.',
                'type': type(exc).__name__,
            },
        }

        # Include traceback in debug mode only
        if settings.DEBUG:
            response_data['error']['detail'] = str(exc)
            response_data['error']['traceback'] = tb

        return JsonResponse(response_data, status=500)

class ActiveCompanyMiddleware:
    """
    Middleware to attach the active company to the request object.
    Uses the 'active_company_id' stored in the session.
    If no company is active in session, automatically falls back to the first available company in the DB.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.core.exceptions import ObjectDoesNotExist
        from company.models import Company
        active_company_id = request.session.get('active_company_id')
        request.active_company = None
        if active_company_id:
            try:
                request.active_company = Company.objects.get(id=active_company_id)
            except ObjectDoesNotExist:
                pass
        
        # Safe production fallback: If no active company is in session, fall back to the first available company in the DB.
        if not request.active_company:
            first_company = Company.objects.first()

            if first_company:
                request.active_company = first_company
                request.session['active_company_id'] = str(first_company.id)
        
        response = self.get_response(request)
        return response
