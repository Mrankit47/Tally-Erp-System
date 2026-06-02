"""
Django base settings for ERP project.

Shared configuration used by both dev and prod environments.
Environment-specific overrides are in dev.py and prod.py.
"""

import os
import sys
import logging
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
import dj_database_url

logger = logging.getLogger(__name__)

# =============================================================================
# PATH CONFIGURATION
# =============================================================================

# BASE_DIR = Major Project/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# =============================================================================
# ENVIRONMENT LOADING
# =============================================================================

# Optionally load .env file for local development if available
try:
    from dotenv import load_dotenv
    if (BASE_DIR / '.env').exists():
        load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass

# Add apps/ directory to Python path so apps can be imported directly
# e.g., 'accounts' instead of 'apps.accounts'
sys.path.insert(0, str(BASE_DIR / 'apps'))

# =============================================================================
# CORE SETTINGS
# =============================================================================

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY environment variable is missing. Please set it in your environment or .env file.")

DEBUG = os.getenv("DEBUG") == "True"

ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = [
    "https://tally-erp-system.onrender.com",
    "https://*.ngrok-free.dev",
    "https://*.ngrok-free.app",
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Custom user model — MUST be set before first migration
AUTH_USER_MODEL = 'accounts.User'

# =============================================================================
# APPLICATION DEFINITION
# =============================================================================

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
]

LOCAL_APPS = [
    'core',
    'accounts',
    'company',
    'ledger',
    'voucher',
    'inventory',
    'reports',
    'tally_integration',
    'taxation',
    'invoicing',
    'ai',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# =============================================================================
# MIDDLEWARE
# =============================================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static files — immediately after SecurityMiddleware
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.ActiveCompanyMiddleware',
    'core.middleware.ErrorHandlingMiddleware',  # Custom global error handler — last
]

# =============================================================================
# URL CONFIGURATION
# =============================================================================

ROOT_URLCONF = 'config.urls'

# =============================================================================
# TEMPLATES
# =============================================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.active_company_context',
            ],
        },
    },
]

# =============================================================================
# WSGI / ASGI
# =============================================================================

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# =============================================================================
# DATABASE — PostgreSQL (Supabase compatible), SQLite fallback
# =============================================================================

_database_url = os.environ.get("DATABASE_URL")
if _database_url:
    DATABASES = {
        "default": dj_database_url.config(default=_database_url)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC FILES
# =============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [BASE_DIR / 'static']

# =============================================================================
# MEDIA FILES
# =============================================================================

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# =============================================================================
# DEFAULT PRIMARY KEY
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# DJANGO REST FRAMEWORK
# =============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.StandardResultsPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# =============================================================================
# CORS CONFIGURATION
# =============================================================================

CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://localhost:5173'
).split(',')

CORS_ALLOW_CREDENTIALS = True

# =============================================================================
# TALLY INTEGRATION
# =============================================================================

TALLY_URL = os.getenv('TALLY_URL', 'https://cut-footprint-chowder.ngrok-free.dev')
TALLY_TIMEOUT = int(os.getenv('TALLY_TIMEOUT', '15'))
TALLY_RETRY_COUNT = int(os.getenv('TALLY_RETRY_COUNT', '3'))

# =============================================================================
# LOGGING
# =============================================================================

LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {module}.{funcName}:{lineno} — {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{asctime}] {levelname} — {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': str(LOG_DIR / 'erp.log'),
            'formatter': 'verbose',
        },
        'security_file': {
            'class': 'logging.FileHandler',
            'filename': str(LOG_DIR / 'security.log'),
            'formatter': 'verbose',
            'level': 'WARNING',
        },
        'error_file': {
            'class': 'logging.FileHandler',
            'filename': str(LOG_DIR / 'error.log'),
            'formatter': 'verbose',
            'level': 'ERROR',
        },
        'ai_file': {
            'class': 'logging.FileHandler',
            'filename': str(LOG_DIR / 'ai.log'),
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security.*': {
            'handlers': ['console', 'security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'apps.ai': {
            'handlers': ['console', 'ai_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# =============================================================================
# AUTHENTICATION
# =============================================================================

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'landing'


