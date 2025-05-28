#!/usr/bin/env python

import os
import sys

settings_module = "fpan.settings"

is_testing = "test" in sys.argv
if is_testing:
    settings_module = "tests.settings_test"

if is_testing:
    import coverage

    os.environ["TESTING"] = "True"
    cov = coverage.coverage(
        source=["fpan", "hms", "reporting"],
        omit=["*/tests/*", "*/migrations/*", "*/commands/*"]
    )
    cov.set_option("report:show_missing", True)
    cov.set_option("report:skip_covered", True)
    cov.erase()
    cov.start()

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

    if is_testing:
        cov.stop()
        cov.save()
        cov.report()
