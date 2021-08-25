# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.core import management

def load_rule_filter(apps, schema_editor):

    management.call_command(
        "extension", "search", "register",
        source="fpan/search/components/rule_filter.py"
    )

def remove_rule_filter(apps, schema_editor):

    management.call_command(
        "extension", "search", "unregister",
        name="Rule Filter"
    )

class Migration(migrations.Migration):

    dependencies = [
        ('fpan', '0015_load_slr_layers'),
    ]

    operations = [
        migrations.RunPython(load_rule_filter, remove_rule_filter)
    ]
