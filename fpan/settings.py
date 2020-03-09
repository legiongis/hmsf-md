"""
Django settings for fpan project.
"""

import os
import sys
import arches
import inspect

try:
    from arches.settings import *
except ImportError:
    pass
    
GOOGLE_ANALYTICS_TRACKING_ID = None
    
APP_NAME = "FPAN"
APP_ROOT = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
STATICFILES_DIRS =  (os.path.join(APP_ROOT, 'media'),) + STATICFILES_DIRS

DATATYPE_LOCATIONS.append('fpan.datatypes')
FUNCTION_LOCATIONS.append('fpan.functions')

TEMPLATES[0]['DIRS'].append(os.path.join(APP_ROOT, 'functions', 'templates'))
TEMPLATES[0]['DIRS'].append(os.path.join(APP_ROOT, 'widgets', 'templates'))
TEMPLATES[0]['DIRS'].insert(0, os.path.join(APP_ROOT, 'templates'))

TEMPLATES[0]['OPTIONS']['context_processors'].append('fpan.utils.context_processors.debug')
TEMPLATES[0]['OPTIONS']['context_processors'].append('fpan.utils.context_processors.user_type')

REPORT_INLINES = {
    "Archaeological Site" : [
        {
            "title":"Scout Reports",
            "inline_model":"Scout Report",
            "node_to_look_in":"FMSF Site ID"
        }
    ],
    "Historic Cemetery" : [
        {
            "title":"Scout Reports",
            "inline_model":"Scout Report",
            "node_to_look_in":"FMSF Site ID"
        }
    ],
    "Historic Structure" : [
        {
            "title":"Scout Reports",
            "inline_model":"Scout Report",
            "node_to_look_in":"FMSF Site ID"
        }
    ],
}

## in FPAN the State filtered access values are set in utils.filter.get_state_node_match()
RESOURCE_MODEL_USER_RESTRICTIONS = {
    'f212980f-d534-11e7-8ca8-94659cf754d0': {
        'public': {
            # 'access_level': 'no_access'
            'access_level':'match_node_value',
            'match_config': {
                'node_name':'Assigned To',
                'match_to':'<username>'
            }
        },
        'scout': {
            'access_level':'match_node_value',
            'match_config': {
                'node_name':'Assigned To',
                'match_to':'<username>'
            }
        },
        'state': {
            'access_level':'match_node_value',
            'match_config': {
                'node_name':'Managing Agency',
                'match_to':'<derived_elsewhere>'
            }
        }
    }
}

TILESERVER_RESTRICTION_BY_GRAPH = {
    'f212980f-d534-11e7-8ca8-94659cf754d0': {
        'allowed_groups': [
            'FMSF','FL_BAR'
        ]
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

MENUS_TO_PRINT = 'Scout Report'

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

## the following two variables should be handled in settings_local.py
SECRET_LOG = "path/to/directory/outside/of/version/control"
PACKAGE_PATH = "path/to/location/of/cloned/fpan-data/repo"

ALLOWED_HOSTS = []

ROOT_URLCONF = 'fpan.urls'

SYSTEM_SETTINGS_LOCAL_PATH = os.path.join(APP_ROOT, 'system_settings', 'System_Settings.json')
WSGI_APPLICATION = 'fpan.wsgi.application'
STATIC_ROOT = '/var/www/media'

from datetime import datetime
timestamp = datetime.now().strftime("%m%d%y-%H%M%S")
RESOURCE_IMPORT_LOG = os.path.join(APP_ROOT, 'logs', 'resource_import-{}.log'.format(timestamp))

# Absolute filesystem path to the directory that will hold user-uploaded files.

MEDIA_ROOT = os.path.join(APP_ROOT)

TILE_CACHE_CONFIG = {
    "name": "Disk",
    "path": os.path.join(APP_ROOT, 'tileserver', 'cache')

    # to reconfigure to use S3 (recommended for production), use the following
    # template:

    # "name": "S3",
    # "bucket": "<bucket name>",
    # "access": "<access key>",
    # "secret": "<secret key>"
}

DEFAULT_FROM_EMAIL = ""
EMAIL_SUBJECT_PREFIX = ""

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
    from settings_local import *
except ImportError:
    pass
    
if not DEBUG:
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True
    SESSION_COOKIE_AGE = 7200 #auto logout after 2 hours
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
            'filename': os.path.join(APP_ROOT, 'logs', 'arches.log'),
            'formatter': 'full'
        },
        'fpan': {
            'level': LOG_LEVEL,  # DEBUG, INFO, WARNING, ERROR
            'class': 'logging.FileHandler',
            'filename': os.path.join(APP_ROOT, 'logs', 'fpan.log'),
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
