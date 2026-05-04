from my_secrets import secrets
from .common_settings import *

DEBUG         = True
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     secrets.DEV_DB_NAME,
        'USER':     secrets.DEV_DB_USER,
        'PASSWORD': secrets.DEV_DB_PASSWORD,
        'HOST':     secrets.DEV_DB_HOST,
        'PORT':     secrets.DEV_DB_PORT,
    },
    # Handy for running tests without Postgres
    'sqlite': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME':   BASE_DIR / 'db.sqlite3',
    },
}

CSRF_TRUSTED_ORIGINS  = ['http://localhost:3000', 'http://localhost:3001']
CSRF_COOKIE_NAME      = 'lcpark-dev-csrftoken'
CSRF_COOKIE_HTTPONLY  = False
CSRF_COOKIE_SECURE    = False

SESSION_COOKIE_NAME        = 'lcpark-dev-sessionid'
SESSION_COOKIE_HTTPONLY    = True
SESSION_COOKIE_AGE         = 2 * 60 * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SECURE      = False

APPLICATION_URL     = 'http://localhost:8000/'
API_PREFIX          = 'lcpark'
LOGOUT_REDIRECT_URL = f'/{API_PREFIX}/admin/'