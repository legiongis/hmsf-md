import os

from fpan.settings import ALLOWED_HOSTS, DATABASES, INSTALLED_APPS, CELERY_BROKER_URL

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

rabbitmq_user = os.environ.get("RABBITMQ_DEFAULT_USER")
rabbitmq_pass = os.environ.get("RABBITMQ_DEFAULT_PASS")
CELERY_BROKER_URL = f"amqp://{rabbitmq_user}:{rabbitmq_pass}@rabbitmq:5672"

INSTALLED_APPS += ("arches_extensions",)

# Allow creation of --test-accounts
ALLOWED_HOSTS += ["*"]

DEBUG = True
MODE = "DEV"
