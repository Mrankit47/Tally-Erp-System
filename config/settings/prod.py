"""
Django production settings.

Extends base settings with security hardening and optimized static file serving.
This file should be activated by setting:
    DJANGO_SETTINGS_MODULE=config.settings.prod
"""

from .base import *  # noqa: F401, F403

import os
import dj_database_url

# =============================================================================
# DEBUG — MUST be False in production
# =============================================================================

DEBUG = True

ALLOWED_HOSTS = ["*"]

# =============================================================================
# DATABASE — PostgreSQL via DATABASE_URL (Render-managed)
# =============================================================================
# On Render, set the DATABASE_URL env var to your managed PostgreSQL's
# Internal Database URL (starts with postgresql://).
# Falls back to the individual DB_* vars from base.py if DATABASE_URL is absent.

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,           # Keep connections open for 10 min
            conn_health_checks=True,    # Verify connections before use
        )
    }

# =============================================================================
# SECURITY SETTINGS
# =============================================================================

# HTTPS enforcement
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Cookie security
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = False
CSRF_COOKIE_HTTPONLY = False

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

# CSRF — trust Render's *.onrender.com domain
CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    'https://*.ngrok-free.dev',
    'https://*.ngrok-free.app',
]

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