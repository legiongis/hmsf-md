# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.core import management

def load_site_filter(apps, schema_editor):

    management.call_command(
        "extension", "register", "search",
        source="fpan/search/components/site_filter.py"
    )

def remove_site_filter(apps, schema_editor):

    management.call_command(
        "extension", "unregister", "search",
        name="Site Filter"
    )

class Migration(migrations.Migration):

    dependencies = [
        ('fpan', '0015_load_slr_layers'),
    ]

    operations = [
        migrations.RunPython(load_site_filter, remove_site_filter)
    ]
