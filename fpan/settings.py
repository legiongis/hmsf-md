"""
Django settings for fpan project.
"""

import os
import sys
import arches
import inspect

try:
    from arches.settings import *
except ImportError as e:
    pass

DOMAIN = "hms.fpan.us"
GOOGLE_ANALYTICS_TRACKING_ID = None

APP_NAME = "FPAN"
APP_ROOT = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
STATICFILES_DIRS =  (os.path.join(APP_ROOT, 'media'),) + STATICFILES_DIRS

LOG_DIR = os.path.join(APP_ROOT, "logs")

DATATYPE_LOCATIONS.append('fpan.datatypes')
FUNCTION_LOCATIONS.append('fpan.functions')

TEMPLATES[0]['DIRS'].append(os.path.join(APP_ROOT, 'functions', 'templates'))
TEMPLATES[0]['DIRS'].append(os.path.join(APP_ROOT, 'widgets', 'templates'))
TEMPLATES[0]['DIRS'].insert(0, os.path.join(APP_ROOT, 'templates'))

TEMPLATES[0]['OPTIONS']['context_processors'].append('fpan.utils.context_processors.debug')
TEMPLATES[0]['OPTIONS']['context_processors'].append('fpan.utils.context_processors.user_type')
TEMPLATES[0]['OPTIONS']['context_processors'].append('fpan.utils.context_processors.widget_data')

SEARCH_COMPONENT_LOCATIONS += ["fpan.search.components"]
ELASTICSEARCH_PREFIX = 'fpan'

# manually disable the shapefile exporter class. This creates a 500 error if
# someone were to hit the shapefile export url somehow.
RESOURCE_FORMATTERS['shp'] = None

DISABLE_PROVISIONAL_EDITING = True
HIDE_EMPTY_NODES_IN_REPORT = True

# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
#         'LOCATION': 'fpan_cachetable',
#     }
# }

## example of the default filter that is applied to anonymous and Scout users.
## the land manager accounts don't reference this setting at all, their permissions
## are all handled in the site_filter component.
RESOURCE_MODEL_USER_RESTRICTIONS = {
    'f212980f-d534-11e7-8ca8-94659cf754d0': {
        'default': {
            'access_level':'attribute_filter',
            'filter_config': {
                'node_name':'Assigned To',
                'value':"<username>"
            }
        }
    },
    '14578901-bd5d-11e9-822a-94659cf754d0': {
        'default': {
            'access_level':'no_access'
        }
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'arches.app.utils.password_validation.NumericPasswordValidator', #Passwords cannot be entirely numeric
    },
    # {
        # 'NAME': 'arches.app.utils.password_validation.SpecialCharacterValidator', #Passwords must contain special characters
        # 'OPTIONS': {
            # 'special_characters': ('!','@','#',')','(','*','&','^','%','$'),
        # }
    # },
    {
        'NAME': 'arches.app.utils.password_validation.HasNumericCharacterValidator', #Passwords must contain 1 or more numbers
    },
    {
        'NAME': 'arches.app.utils.password_validation.HasUpperAndLowerCaseValidator', #Passwords must contain upper and lower characters
    },
    {
        'NAME': 'arches.app.utils.password_validation.MinLengthValidator', #Passwords must meet minimum length requirement
        'OPTIONS': {
            'min_length': 6,
        }
    },
]

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '&cu1l36s)wxa@5yxefgdd-wkwpyw3tz2vru*ja@nh*r4*47^15'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

DATABASES = {
    "default": {
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "HOST": "localhost",
        "USER": "postgres",
        "PASSWORD": "postgis",
        "NAME": "fpan",
        "OPTIONS": {},
        "PORT": "5432",
        "POSTGIS_TEMPLATE": "template_postgis_20",
        "TEST": {
            "CHARSET": None,
            "COLLATION": None,
            "MIRROR": None,
            "NAME": None
        },
        "TIME_ZONE": None
    }
}

INSTALLED_APPS+=('fpan', 'hms')

# the code should be refactored to not even use SECRET_LOG anymore...
SECRET_LOG = LOG_DIR
PACKAGE_PATH = os.path.join(os.path.dirname(os.path.dirname(APP_ROOT)), "fpan-data")

ALLOWED_HOSTS = []

ROOT_URLCONF = 'fpan.urls'

SYSTEM_SETTINGS_LOCAL_PATH = os.path.join(APP_ROOT, 'system_settings', 'System_Settings.json')
WSGI_APPLICATION = 'fpan.wsgi.application'
STATIC_ROOT = '/var/www/media'

from datetime import datetime
timestamp = datetime.now().strftime("%m%d%y-%H%M%S")
RESOURCE_IMPORT_LOG = os.path.join(LOG_DIR, 'resource_import-{}.log'.format(timestamp))

# Absolute filesystem path to the directory that will hold user-uploaded files.

MEDIA_ROOT = os.path.join(APP_ROOT)

DEFAULT_FROM_EMAIL = 'no-reply@fpan.us'
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

# Use Nose for running tests - errors occur unless you run test modules individually
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


try:
    from .settings_local import *
except ImportError as e:
    pass

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True
    SESSION_COOKIE_AGE = 600 #auto logout after 2 hours
    SESSION_SAVE_EVERY_REQUEST = True

# set log level to info, unless debug is true (which would be set in settings_local.py
LOG_LEVEL = 'INFO'
if DEBUG is True:
    LOG_LEVEL = 'DEBUG'

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
from django.utils.translation import gettext_lazy as _

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
