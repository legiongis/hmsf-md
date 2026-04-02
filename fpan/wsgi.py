import os
import sys
import inspect

path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))  # pyright: ignore[reportArgumentType]

if path not in sys.path:
    sys.path.append(path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fpan.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

from arches.app.models.system_settings import settings
settings.update_from_db()
