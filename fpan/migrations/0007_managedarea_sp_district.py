# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-11-03 18:36
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fpan', '0006_managedarea_nickname'),
    ]

    operations = [
        migrations.AddField(
            model_name='managedarea',
            name='sp_district',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]