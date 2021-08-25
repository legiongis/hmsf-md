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

APP_NAME = "FPAN"
APP_ROOT = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

LOG_DIR = os.path.join(APP_ROOT, "logs")

MEDIA_ROOT = os.path.join(APP_ROOT)
STATIC_ROOT = os.path.join(APP_ROOT, 'static')

ROOT_URLCONF = 'fpan.urls'
WSGI_APPLICATION = 'fpan.wsgi.application'

STATICFILES_DIRS = (os.path.join(APP_ROOT, 'media'),) + STATICFILES_DIRS

DATATYPE_LOCATIONS.append('fpan.datatypes')
FUNCTION_LOCATIONS.append('fpan.functions')

TEMPLATES[0]['DIRS'].append(os.path.join(APP_ROOT, 'functions', 'templates'))
TEMPLATES[0]['DIRS'].append(os.path.join(APP_ROOT, 'widgets', 'templates'))
TEMPLATES[0]['DIRS'].insert(0, os.path.join(APP_ROOT, 'templates'))

TEMPLATES[0]['OPTIONS']['context_processors'].append('fpan.utils.context_processors.debug')
TEMPLATES[0]['OPTIONS']['context_processors'].append('fpan.utils.context_processors.user_type')
TEMPLATES[0]['OPTIONS']['context_processors'].append('fpan.utils.context_processors.widget_data')

SEARCH_COMPONENT_LOCATIONS += ["fpan.search.components"]

INSTALLED_APPS += ('fpan', 'hms')

SYSTEM_SETTINGS_LOCAL_PATH = os.path.join(APP_ROOT, "system_settings", "System_Settings.json")

ELASTICSEARCH_PREFIX = 'fpan'

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

try:
    from .settings_local import *
except ImportError as e:
    pass

# Use Nose for running tests - errors occur unless you run test modules individually
if MODE == "DEV":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        import logging
        logging.disable(logging.CRITICAL)

    INSTALLED_APPS += ('django_nose', )
    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
    NOSE_ARGS = [
        '--with-coverage',
        '--nologcapture',
        '--cover-package=fpan',
        '--verbosity=3',
        '--cover-erase',
    ]

    LOG_LEVEL = 'DEBUG'

if MODE == "PROD":
    SESSION_COOKIE_SAMESITE = 'Strict'
    SESSION_COOKIE_AGE = 1800 #auto logout after 1/2 hour

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
    'handlers': {
        'arches': {
            'level': LOG_LEVEL,  # DEBUG, INFO, WARNING, ERROR
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'arches.log'),
            'formatter': 'full'
        },
        'fpan': {
            'level': LOG_LEVEL,  # DEBUG, INFO, WARNING, ERROR
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'fpan.log'),
            'formatter': 'full'
        },
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'console'
        }
    },
    'loggers': {
        'arches': {
            'handlers': ['arches', 'console'],
            'level': LOG_LEVEL,
            'propagate': True
        },
        'fpan': {
            'handlers': ['fpan', 'console'],
            'level': LOG_LEVEL,
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
