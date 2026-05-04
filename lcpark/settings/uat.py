from my_secrets import secrets
from .common_settings import *

DEBUG         = False
ALLOWED_HOSTS = ['staging.amns.in']

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     secrets.DEV_DB_NAME,
        'USER':     secrets.DEV_DB_USER,
        'PASSWORD': secrets.DEV_DB_PASSWORD,
        'HOST':     secrets.DEV_DB_HOST,
        'PORT':     secrets.DEV_DB_PORT,
    },
}

CSRF_TRUSTED_ORIGINS  = ['https://*.myamns.in', 'https://*.amns.in']
CSRF_COOKIE_NAME      = 'lcpark-uat-csrftoken'
CSRF_COOKIE_HTTPONLY  = False
CSRF_COOKIE_SECURE    = True

SESSION_COOKIE_NAME        = 'lcpark-uat-sessionid'
SESSION_COOKIE_HTTPONLY    = True
SESSION_COOKIE_AGE         = 2 * 60 * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SECURE      = True

# Override common default to point at staging
LANDING_PAGE_FMT    = "https://staging.amns.in/LC/ApprovalForm/{}"

APPLICATION_URL     = 'https://staging.amns.in/'
API_PREFIX          = 'lcpark'
LOGOUT_REDIRECT_URL = f'/{API_PREFIX}/admin/'