# Generated by Django 2.2.13 on 2021-08-23 16:02

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hms', '0010_auto_20210816_1032'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scoutprofile',
            name='background',
            field=models.TextField(blank=True, null=True, verbose_name='Please let us know a little about your education and occupation.'),
        ),
        migrations.AlterField(
            model_name='scoutprofile',
            name='city',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='scoutprofile',
            name='interest_reason',
            field=models.TextField(blank=True, null=True, verbose_name='Why are you interested in becoming a Heritage Monitoring Scout?'),
        ),
        migrations.AlterField(
            model_name='scoutprofile',
            name='phone',
            field=models.CharField(blank=True, max_length=12, null=True),
        ),
        migrations.AlterField(
            model_name='scoutprofile',
            name='relevant_experience',
            field=models.TextField(blank=True, null=True, verbose_name='Please let us know about any relevant experience.'),
        ),
        migrations.AlterField(
            model_name='scoutprofile',
            name='site_interest_type',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, choices=[('Prehistoric', 'Prehistoric'), ('Historic', 'Historic'), ('Cemeteries', 'Cemeteries'), ('Underwater', 'Underwater'), ('Other', 'Other')], max_length=30), default=list, size=None),
        ),
        migrations.AlterField(
            model_name='scoutprofile',
            name='state',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='scoutprofile',
            name='street_address',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='scoutprofile',
            name='zip_code',
            field=models.CharField(blank=True, max_length=5, null=True),
        ),
    ]