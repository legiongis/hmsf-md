# Generated by Django 2.2.13 on 2021-01-09 13:33

from django.conf import settings
import django.contrib.auth.models
import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
        ('hms', '0002_auto_20171201_1646'),
    ]

    operations = [
        migrations.CreateModel(
            name='LandManager',
            fields=[
                ('user_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Land Manager',
                'verbose_name_plural': 'Land Managers',
            },
            bases=('auth.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='ManagementAgency',
            fields=[
                ('code', models.CharField(max_length=20, primary_key=True, serialize=False)),
                ('name', models.CharField(blank=True, max_length=200, null=True)),
            ],
            options={
                'verbose_name': 'Management Agency',
                'verbose_name_plural': 'Management Agencies',
            },
        ),
        migrations.CreateModel(
            name='ManagementArea',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=254)),
                ('description', models.CharField(blank=True, max_length=254, null=True)),
                ('nickname', models.CharField(blank=True, max_length=30, null=True)),
                ('geom', django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326)),
                ('management_agency', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='hms.ManagementAgency')),
            ],
            options={
                'verbose_name': 'Management Area',
                'verbose_name_plural': 'Management Areas',
            },
        ),
        migrations.CreateModel(
            name='ManagementAreaGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('note', models.CharField(max_length=255)),
                ('areas', models.ManyToManyField(to='hms.ManagementArea')),
            ],
            options={
                'verbose_name': 'Management Area Group',
                'verbose_name_plural': 'Management Area Groups',
            },
        ),
        migrations.CreateModel(
            name='LandManagerProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_access', models.BooleanField(default=False, help_text='Give this user access to all Archaeological Sites.')),
                ('apply_agency_filter', models.BooleanField(blank=True, default=False, help_text='Give this user access to all Archaeological Sites managedby their Agency (as defined above).', null=True)),
                ('apply_area_filter', models.BooleanField(blank=True, default=False, help_text='Give this user access to all Archaeological Sites within any of the specified areas or groups of areas below.', null=True)),
                ('grouped_areas', models.ManyToManyField(to='hms.ManagementAreaGroup')),
                ('individual_areas', models.ManyToManyField(to='hms.ManagementArea')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='user', to='hms.LandManager')),
            ],
        ),
    ]