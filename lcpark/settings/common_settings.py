"""
Common Django settings for lcpark project.
Environment-specific overrides live in dev.py and uat.py.
"""
import os
from pathlib import Path

from my_secrets import secrets

# BASE_DIR is the repo root (parent of the lcpark/ package).
# Path: <repo_root>/lcpark/settings/common_settings.py → .parent.parent.parent
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = secrets.SECRET_KEY

ALLOWED_HOSTS = ['*']

# ── Apps ──────────────────────────────────────────────────────────────────────
DEPENDENCY_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'api',
    'workflow',
    'rbac',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'reversion',
    'reversion_compare',
]

PROJECT_APPS = ['masters', 'lc_request']

INSTALLED_APPS = DEPENDENCY_APPS + PROJECT_APPS

# ── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ORIGIN_ALLOW_ALL    = True
CORS_ALLOW_CREDENTIALS   = True
CORS_ALLOW_METHODS       = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']
CORS_ALLOW_HEADERS       = [
    'accept', 'accept-encoding', 'approval-authorization', 'authorization',
    'content-type', 'dnt', 'origin', 'user-agent', 'x-csrftoken',
    'x-requested-with', 'req', 'source',
]

ROOT_URLCONF = 'lcpark.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'lcpark.wsgi.application'

# ── REST Framework ────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_METADATA_CLASS':       'api.metadata.MinimalMetadata',
    'DEFAULT_PAGINATION_CLASS':     'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE':                    10,
    'DEFAULT_SCHEMA_CLASS':         'rest_framework.schemas.coreapi.AutoSchema',
}

# ── Cache ─────────────────────────────────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND':  'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# ── Auth ──────────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── i18n ──────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'UTC'
USE_I18N      = True
USE_TZ        = True

# ── Static / Media ────────────────────────────────────────────────────────────
STATIC_URL  = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
MEDIA_ROOT  = os.path.join(BASE_DIR, 'media')
MEDIA_URL   = '/media/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
X_FRAME_OPTIONS    = 'SAMEORIGIN'

# ── S3 ────────────────────────────────────────────────────────────────────────
S3_BUCKET_NAME = secrets.S3_BUCKET_NAME

# ── Project-specific framework config ────────────────────────────────────────
MODEL_VALIDATORS = {}

DISPLAY_MODELS = {
    'sodata':   'Sodata',
    'itemdata': 'Itemdata',
}

DISPLAY_MODEL_FIELDS = {
    'sodata':   ['so_id', 'so_number', 'plant_code', 'customer_code', 'ship_to_party',
                 'so_value', 'pyt_terms', 'remarks', 'cust_reference', 'cust_reference_date',
                 'inco_terms', 'inco_location', 'status'],
    'itemdata': ['so_id', 'so_number', 'item_number', 'material_no', 'material_qty',
                 'unit', 'material_price', 'matl_value'],
}

AUTO_GENERATION_SECTIONS = ['MASTERS']

EXTRA_USER_META = {
    'MASTERS': [
        {'app': 'masters', 'model': 'sodata',  'title': 'SO Data'},
        {'app': 'masters', 'model': 'itemdata', 'title': 'Item Data'},
    ],
    'lc_request': [
        {'screen': 'lc_request', 'title': 'LC Request', 'type': 'subsection'},
    ],
}

SECTION_ICONS = {
    'MASTERS':    'TableOutlined',
    'lc_request': 'CheckCircleOutlined',
}

URL_METADATA_CLASS = {
    'api':        'api.metadata.ApiMetadata',
    'User':       'rbac.metadata.RbacMetadata',
    'Suggest':    'rbac.metadata.RbacMetadata',
    'Group':      'rbac.metadata.RbacMetadata',
    'Permission': 'rbac.metadata.RbacMetadata',
}

MODEL_FIELD_CHOICES    = {}
MASTERS_APP_RBAC       = 'masters'
MASTERS_APP_NAME       = 'masters'

APPLY_SEARCH_MODEL_FIELDS = {
    'sodata':   ['so_id', 'so_number', 'company_code', 'plant_code', 'customer_code',
                 'ship_to_party', 'so_value', 'pyt_terms', 'remarks', 'cust_reference',
                 'cust_reference_date', 'inco_terms', 'inco_location'],
    'itemdata': ['so_id', 'so_number', 'item_number', 'material_no', 'material_qty',
                 'unit', 'material_price', 'matl_value'],
}

FOREIGN_KEY_UI_NAME_MAP = {}

WORKFLOW_EMAIL_POLICY = {
    'default': {
        'Init':    {'request': 'workflow.email_policy.notify_next_level'},
        'Approve': {
            'request':      'workflow.email_policy.notify_next_level',
            'notification': 'workflow.email_policy.get_request_initiator',
        },
        'Reject':  {'notification': 'workflow.email_policy.notify_the_hierarchy'},
    }
}

RABBITMQ_CONF = {
    "RABBITMQ_CON_URL": "",
    "RABBITMQ_QUEUE":   "",
    "SENDER_MAIL":      "",
    "MAIL_CREDENTIALS": {"sender_email": "", "mailserver": ""},
}

WORKFLOW_MAIL_MAP          = {}
MODELS_WITH_MAIL_APPROVAL  = []
LANDING_PAGE_FMT           = "http://localhost:3000/LC/ApprovalForm/{}"
APPROVAL_API_URLS          = {}

DATE_INPUT_FORMAT          = []
DATE_TIME_INPUT_FORMAT     = ['iso-8601']
TIME_INPUT_FORMAT          = []

POST_SAVE_OBJ_RETURN_HOOKS = {}

CHECK_USER_REGISTRATION    = False
USER_PROFILE_MODEL_DETAILS = {'app': '', 'model': '', 'search_on_field': ''}
USER_PROFILE_SERIALIZER    = ''

DATA_RESTRICT_PERMISSIONS  = {}

MASTER_FILES_MOSS_UPLOAD       = False
MOSS_BASE_URL                  = ''
MOSS_USERNAME                  = ''
MOSS_PASSWORD                  = ''
RELATIVE_FOLDER_TO_UPLOAD_URL  = ''

TRANS_FILTER_QS_SERIALIZER = {}
EXCEL_IMPORT_CONFIGS       = {}
WORKFLOW_MODEL_LIST        = []
WORKFLOW_EMAIL_CONFIGS     = {}
APPROVAL_GROUPS            = []
GROUP_WISE_STATUS_MAPPING  = {}
EXCEL_EXPORT_CONFIGS       = {}