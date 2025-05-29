import os

from .settings import ALLOWED_HOSTS, DATABASES, INSTALLED_APPS

DATABASES["default"]["USER"] = os.environ.get("PGUSERNAME", "username")
DATABASES["default"]["PASSWORD"] = os.environ.get("PGPASSWORD", "password")
DATABASES["default"]["HOST"] = os.environ.get("PGHOST", "localhost")
DATABASES["default"]["PORT"] = os.environ.get("PGPORT", "5432")

ELASTICSEARCH_HOSTS = [
    {
        "host": os.environ.get("ESHOST", "localhost"),
        "port": int(os.environ.get("ESPORT", "9200")),
    }
]

INSTALLED_APPS += ("arches_extensions",)

# Allow creation of --test-accounts
ALLOWED_HOSTS += ["*"]

DEBUG = True
MODE = "DEV"
