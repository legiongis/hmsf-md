"""
Django settings for fpan project.
"""

import os
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

## in fpan app, the Scout and State filtered access values are set elsewhere
RESOURCE_MODEL_USER_RESTRICTIONS = {
    'f212980f-d534-11e7-8ca8-94659cf754d0': {
        'default': {
            'level': 'no_access',
            'term_filter': {
                # 'node_name':'<insert name of node>',
                # 'value':'<insert string value to test>'
            }
        },
        'Scout': {
            'level':'term_filter',
            'term_filter': {
                'node_name':'Assigned To',
                'value':'derived_string'
            }
        },
        'State': {
            'level':'term_filter',
            'term_filter': {
                'node_name':'Managing Agency',
                'value':'derived_string'
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

LOGGING = {   'disable_existing_loggers': False,
    'handlers': {   'file': {   'class': 'logging.FileHandler',
                                'filename': os.path.join(APP_ROOT, 'arches.log'),
                                'level': 'DEBUG'}},
    'loggers': {   'arches': {   'handlers': [   'file'],
                                 'level': 'DEBUG',
                                 'propagate': True}},
    'version': 1}

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

try:
    from settings_local import *
except ImportError:
    pass
    
if not DEBUG:
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True
    SESSION_COOKIE_AGE = 7200 #auto logout after 2 hours
    SESSION_SAVE_EVERY_REQUEST = True
