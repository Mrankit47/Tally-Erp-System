"""
Global context processors for the ERP system.

These inject common template variables into EVERY page without
needing to add them to each view's context manually.
"""

from company.models import Company


def active_company_context(request):
    """
    Injects 'active_company' and 'all_companies' into every template context.
    This powers the company selector dropdown in base.html's top bar.
    """
    return {
        'active_company': getattr(request, 'active_company', None),
        'all_companies': Company.objects.all(),
    }
