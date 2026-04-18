"""
Standard pagination for DRF API responses.

Provides consistent page-based pagination across all endpoints.
Page size can be overridden per-request via the `page_size` query parameter.
"""

from rest_framework.pagination import PageNumberPagination


class StandardResultsPagination(PageNumberPagination):
    """
    Standard pagination class for all API endpoints.

    Query parameters:
        page: Page number (default: 1)
        page_size: Number of results per page (default: 20, max: 100)

    Example: /api/v1/accounts/users/?page=2&page_size=50
    """

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
