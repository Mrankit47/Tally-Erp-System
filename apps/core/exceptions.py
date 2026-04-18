"""
Custom DRF exception handler.

Wraps DRF's default exception handling to provide a consistent
response envelope: { success, error, data }.

This ensures all API errors — validation, authentication, permission,
and server errors — share the same response shape.
"""

import logging

from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that wraps DRF responses in a standard envelope.

    Response format:
        {
            "success": false,
            "error": {
                "message": "...",
                "type": "ValidationError",
                "details": { ... }   # original DRF error data
            }
        }
    """
    # Call DRF's default handler first to get the standard error response
    response = exception_handler(exc, context)

    if response is not None:
        # Log the error with request context
        view = context.get('view', None)
        view_name = view.__class__.__name__ if view else 'UnknownView'

        logger.warning(
            'API exception in %s: [%s] %s',
            view_name,
            type(exc).__name__,
            str(exc),
        )

        # Wrap the response in our standard envelope
        wrapped_data = {
            'success': False,
            'error': {
                'message': _get_error_message(response.data),
                'type': type(exc).__name__,
                'details': response.data,
            },
        }

        response.data = wrapped_data

    return response


def _get_error_message(data):
    """
    Extract a human-readable error message from DRF error data.

    DRF error data can be a dict, list, or string. This function
    normalizes it into a single readable message.
    """
    if isinstance(data, dict):
        # Get the first error message from the dict
        if 'detail' in data:
            return str(data['detail'])
        # Return the first field error
        for field, errors in data.items():
            if isinstance(errors, list):
                return f'{field}: {errors[0]}'
            return f'{field}: {errors}'
    elif isinstance(data, list):
        return str(data[0])
    return str(data)
