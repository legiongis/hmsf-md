import os
import inspect
from django.utils.translation import gettext_lazy as _

try:
    from arches.settings import *
except ImportError as e:
    pass

DEBUG = False
HTTPS = False
MODE = "PROD"

APP_NAME = "HMS - FPAN"
APP_ROOT = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

LOG_DIR = os.path.join(APP_ROOT, "logs")

MEDIA_ROOT = os.path.join(APP_ROOT)
STATIC_ROOT = os.path.join(APP_ROOT, 'static')

ROOT_URLCONF = 'fpan.urls'
WSGI_APPLICATION = 'fpan.wsgi.application'

STATICFILES_DIRS = (os.path.join(APP_ROOT, 'media'),) + STATICFILES_DIRS

## new setting in 6.1  -AC 07/28/2022
EXPORT_DATA_FIELDS_IN_CARD_ORDER = True

CELERY_BROKER_URL = "amqp://username:password@localhost:5672"

TEST_DATA_DIR = os.path.join(os.path.dirname(APP_ROOT), "tests", "data")

## seems to cause errors still, disabling
##SEARCH_EXPORT_IMMEDIATE_DOWNLOAD_THRESHOLD = 4000

DATATYPE_LOCATIONS.append('fpan.datatypes')
FUNCTION_LOCATIONS.append('fpan.functions')
ETL_MODULE_LOCATIONS.append('fpan.etl_modules')

TEMPLATES[0]['DIRS'].append(os.path.join(APP_ROOT, 'functions', 'templates'))
TEMPLATES[0]['DIRS'].append(os.path.join(APP_ROOT, 'widgets', 'templates'))
TEMPLATES[0]['DIRS'].insert(0, os.path.join(APP_ROOT, 'templates'))
TEMPLATES[0]['DIRS'].insert(0, os.path.join(os.path.dirname(APP_ROOT), 'site_theme', 'templates'))

TEMPLATES[0]['OPTIONS']['context_processors'].append('fpan.context_processors.debug')
TEMPLATES[0]['OPTIONS']['context_processors'].append('fpan.context_processors.widget_data')
TEMPLATES[0]['OPTIONS']['context_processors'].append('fpan.context_processors.management_area_importer_configs')
TEMPLATES[0]['OPTIONS']['context_processors'].append('fpan.context_processors.rule_filter_html')
TEMPLATES[0]['OPTIONS']['context_processors'].append('hms.context_processors.user_type')
TEMPLATES[0]['OPTIONS']['context_processors'].append('site_theme.context_processors.profile_content')

SEARCH_COMPONENT_LOCATIONS += ["fpan.search.components"]

# some shenanigans because grappelli must precede the django.contrib.admin app
INSTALLED_APPS = tuple([i for i in INSTALLED_APPS if not i == "django.contrib.admin"])
INSTALLED_APPS += ('grappelli', 'django.contrib.admin')

GRAPPELLI_ADMIN_TITLE = "HMS Florida - Monitoring Database"

DOCS_ROOT = os.path.join(os.path.dirname(APP_ROOT), 'docs/_build/dirhtml')
DOCS_ACCESS = 'staff'
DOCS_DIRHTML = True

INSTALLED_APPS += (
    'fpan',         # this is the Arches "project"
    'hms',          # HMS accounts, permissions, models, etc.
    'reporting',    # stats and email reporting
    'site_theme',   # lightweight app to hold models for front end theming
    'tinymce',      # used for WISIWYG editor in site_theme admin pages
    'docs',         # django-docs implementation: https://github.com/littlepea/django-docs/
)

PLAUSIBLE_SITE_DOMAIN = None
PLAUSIBLE_EMBED_LINK = None

SYSTEM_SETTINGS_LOCAL_PATH = os.path.join(APP_ROOT, "system_settings", "System_Settings.json")

ELASTICSEARCH_PREFIX = 'fpan'

DEPRECATE_LEGACY_FIXTURE_LOAD = True
DEPRECATE_LEGACY_FIXTURE_LOAD_MSG = " \033[01m\033[94m DEPRECATED: operations skipped\033[0m"

# manually disable the shapefile exporter class. This creates a 500 error if
# someone were to hit the shapefile export url somehow.
RESOURCE_FORMATTERS['shp'] = None

DISABLE_PROVISIONAL_EDITING = True
HIDE_EMPTY_NODES_IN_REPORT = True

AUTH_PASSWORD_VALIDATORS = [
    #Passwords cannot be entirely numeric
    {'NAME': 'arches.app.utils.password_validation.NumericPasswordValidator'},
    #Passwords must contain 1 or more numbers
    {'NAME': 'arches.app.utils.password_validation.HasNumericCharacterValidator'},
    #Passwords must contain upper and lower characters
    {'NAME': 'arches.app.utils.password_validation.HasUpperAndLowerCaseValidator'},
    #Passwords must meet minimum length requirement
    {'NAME': 'arches.app.utils.password_validation.MinLengthValidator',
     'OPTIONS': {'min_length': 6}},
]

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '&cu1l36s)wxa@5yxefgdd-wkwpyw3tz2vru*ja@nh*r4*47^15'

# project-specific database settings, inherit the rest from arches.settings
DATABASES["default"]["NAME"] = "fpan"
DATABASES["default"]["POSTGIS_TEMPLATE"] = "template_postgis_20"

ALLOWED_HOSTS = []

## this should be changed in core Arches so the log is just in LOG_DIR
from datetime import datetime
timestamp = datetime.now().strftime("%m%d%y-%H%M%S")
RESOURCE_IMPORT_LOG = os.path.join(LOG_DIR, 'resource_import-{}.log'.format(timestamp))

DEFAULT_FROM_EMAIL = 'no-reply@hms.fpan.us'
EMAIL_SUBJECT_PREFIX = '[HMS] '

# put ADMINS and MANAGERS contact info in settings_local.py
# these addresses will get emails from application errors
ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)
MANAGERS = ADMINS

# also put these in settings_local.py. These addresses will
# get database summaries and updates (not errors)
FPAN_ADMINS = (
    # ('Your Name', 'your_email@Example.com'),
)

LOG_LEVEL = 'INFO'

## make sure this stays False
SESSION_SAVE_EVERY_REQUEST = False

## Full config with node ids used in spatial join
SPATIAL_JOIN_GRAPHID_LOOKUP = {
    "Archaeological Site": {
        "Nodegroup": "4259ff42-715c-11ee-9e57-4df2569ff543",
        "County": "64f9a4da-715c-11ee-9e57-4df2569ff543",
        "FPAN Region": "4d1dc620-715c-11ee-9e57-4df2569ff543",
        "Management Area": "877fefaa-715c-11ee-9e57-4df2569ff543",
        "Management Agency": "58908172-715d-11ee-9e57-4df2569ff543",
        "Assigned To": "4d11bac0-d535-11e7-a1b3-94659cf754d0",
    },
    "Historic Cemetery": {
        "Nodegroup": "48821219-715e-11ee-9e57-4df2569ff543",
        "County": "4882121d-715e-11ee-9e57-4df2569ff543",
        "FPAN Region": "4882121c-715e-11ee-9e57-4df2569ff543",
        "Management Area": "4882121e-715e-11ee-9e57-4df2569ff543",
        "Management Agency": "4882121b-715e-11ee-9e57-4df2569ff543",
    },
    "Historic Structure": {
        "Nodegroup": "ad51e45d-715e-11ee-9e57-4df2569ff543",
        "County": "ad51e461-715e-11ee-9e57-4df2569ff543",
        "FPAN Region": "ad51e460-715e-11ee-9e57-4df2569ff543",
        "Management Area": "ad51e45f-715e-11ee-9e57-4df2569ff543",
        "Management Agency": "ad51e462-715e-11ee-9e57-4df2569ff543",
    },
}

try:
    from .settings_local import *
except ImportError as e:
    pass

if MODE == "DEV":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        import logging
        logging.disable(logging.CRITICAL)

    LOG_LEVEL = 'DEBUG'

if MODE == "PROD":
    SESSION_COOKIE_SAMESITE = 'Strict'
    SESSION_COOKIE_AGE = 28800 # auto logout after 8 hrs

if HTTPS:
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_SESSION_REDIRECT = True
    CSRF_COOKIE_SECURE = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'full': {
            'format': '%(asctime)s %(name)s:%(lineno)d %(levelname)s %(message)s',
        },
        'console': {
            'format': '%(message)s',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'arches': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'arches-debug.log'),
            'formatter': 'full'
        },
        'fpan': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'fpan-debug.log'),
            'formatter': 'full'
        },
        'hms': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'hms-debug.log'),
            'formatter': 'full'
        },
        'error': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'error.log'),
            'formatter': 'full',
        },
        'info': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'info.log'),
            'formatter': 'full',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'console',
            'filters': ['require_debug_true'],
        }
    },
    'loggers': {
        'arches': {
            'handlers': ['arches', 'info', 'error', 'console'],
            'level': 'DEBUG',
            'propagate': True
        },
        'fpan': {
            'handlers': ['fpan', 'info', 'error', 'console'],
            'level': 'DEBUG',
            'propagate': True
        },
        'hms': {
            'handlers': ['hms', 'info', 'error', 'console'],
            'level': 'DEBUG',
            'propagate': True
        }
    }
}

# support localization


MIDDLEWARE = [
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    #'arches.app.utils.middleware.TokenMiddleware',
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "arches.app.utils.middleware.ModifyAuthorizationHeader",
    "oauth2_provider.middleware.OAuth2TokenMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    # "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "arches.app.utils.middleware.SetAnonymousUser",
]

# default language of the application
# language code needs to be all lower case with the form:
# {langcode}-{regioncode} eg: en, en-gb ....
# a list of language codes can be found here http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = "en"
# list of languages to display in the language switcher,
# if left empty or with a single entry then the switch won't be displayed
# language codes need to be all lower case with the form:
# {langcode}-{regioncode} eg: en, en-gb ....
# a list of language codes can be found here http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGES = [
        ('en', _('English')),
        ]
# override this to permenantly display/hide the language switcher
SHOW_LANGUAGE_SWITCH = len(LANGUAGES) > 1
