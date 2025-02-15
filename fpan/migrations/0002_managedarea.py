# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-11-27 11:59
from __future__ import unicode_literals

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fpan', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ManagedArea',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=254)),
                ('agency', models.CharField(choices=[(b'FL Dept. of Environmental Protection, Div. of Recreation and Parks', b'FL Dept. of Environmental Protection, Div. of Recreation and Parks'), (b'FL Dept. of Agriculture and Consumer Services, Florida Forest Service', b'FL Dept. of Agriculture and Consumer Services, Florida Forest Service'), (b'FL Fish and Wildlife Conservation Commission', b'FL Fish and Wildlife Conservation Commission'), (b'FL Dept. of Environmental Protection, Florida Coastal Office', b'FL Dept. of Environmental Protection, Florida Coastal Office')], max_length=254)),
                ('category', models.CharField(choices=[(b'State Parks', b'State Parks'), (b'State Forest', b'State Forest'), (b'Fish and Wildlife Conservation Commission', b'Fish and Wildlife Conservation Commission'), (b'Aquatic Preserves', b'Aquatic Preserves')], max_length=254)),
                ('geom', django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326)),
            ],
        ),
    ]
