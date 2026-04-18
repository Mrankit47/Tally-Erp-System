"""
Django production settings.

Extends base settings with security hardening and optimized static file serving.
This file should be activated by setting:
    DJANGO_SETTINGS_MODULE=config.settings.prod
"""

from .base import *  # noqa: F401, F403

import os

# =============================================================================
# DEBUG — MUST be False in production
# =============================================================================

DEBUG = False

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# =============================================================================
# SECURITY SETTINGS
# =============================================================================

# HTTPS enforcement
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Cookie security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# HSTS — tell browsers to only use HTTPS for 1 year
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Prevent content type sniffing
SECURE_CONTENT_TYPE_NOSNIFF = True

# XSS protection
SECURE_BROWSER_XSS_FILTER = True

# Clickjacking protection
X_FRAME_OPTIONS = 'DENY'

# =============================================================================
# STATIC FILES — WhiteNoise (compressed + cached)
# =============================================================================

STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# =============================================================================
# LOGGING — Less verbose, file-focused
# =============================================================================

LOGGING['root']['level'] = 'WARNING'
LOGGING['loggers']['django']['level'] = 'WARNING'
LOGGING['loggers']['django.request']['level'] = 'ERROR'
LOGGING['loggers']['apps']['level'] = 'WARNING'

# =============================================================================
# DRF — JSON only in production (no browsable API)
# =============================================================================

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
]
