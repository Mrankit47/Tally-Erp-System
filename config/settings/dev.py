"""
Django development settings.

Extends base settings with development-friendly overrides.
Uses SQLite as fallback if PostgreSQL env vars are not provided.
"""

from .base import *  # noqa: F401, F403

# =============================================================================
# DEBUG
# =============================================================================

DEBUG = True

ALLOWED_HOSTS = ['*']

# =============================================================================
# DATABASE — SQLite fallback for quick local development
# =============================================================================

import os

if not os.getenv('DATABASE_URL'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# =============================================================================
# EMAIL — Console backend for development
# =============================================================================

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# =============================================================================
# CORS — Allow all origins in development
# =============================================================================

CORS_ALLOW_ALL_ORIGINS = True

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "http://localhost:8000"
]
# =============================================================================
# LOGGING — More verbose in development
# =============================================================================

LOGGING['root']['level'] = 'DEBUG'
LOGGING['loggers']['apps']['level'] = 'DEBUG'

# =============================================================================
# DRF — Enable browsable API in development
# =============================================================================

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
]
