# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.core import management

def load_rule_filter(apps, schema_editor):

    management.call_command(
        "extension", "register", "search-filter",
        source="fpan/search/components/rule_filter.py",
        overwrite=True,
    )

def remove_rule_filter(apps, schema_editor):

    management.call_command(
        "extension", "unregister", "search-filter",
        name="Rule Filter"
    )

class Migration(migrations.Migration):

    dependencies = [
        ('fpan', '0015_load_slr_layers'),
    ]

    operations = [
        migrations.RunPython(load_rule_filter, remove_rule_filter)
    ]
