# Generated by Django 2.2.13 on 2021-01-31 23:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hms', '0003_landmanager_managementagency_managementarea_managementareagroup'),
    ]

    operations = [
        migrations.CreateModel(
            name='ManagementAreaCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
            ],
            options={
                'verbose_name': 'Management Area Category',
                'verbose_name_plural': 'Management Area Categories',
            },
        ),
        migrations.AddField(
            model_name='managementarea',
            name='management_level',
            field=models.CharField(blank=True, choices=[('Federal', 'Federal'), ('State', 'State'), ('County', 'County'), ('City', 'City')], help_text='Used for internal management. Not linked to permissions rules.', max_length=25, null=True),
        ),
        migrations.AlterField(
            model_name='managementarea',
            name='management_agency',
            field=models.ForeignKey(blank=True, help_text='Used to grant access to Land Managers whose accounts have the Agency Filter applied.', null=True, on_delete=django.db.models.deletion.CASCADE, to='hms.ManagementAgency'),
        ),
        migrations.AddField(
            model_name='managementarea',
            name='category',
            field=models.ForeignKey(blank=True, help_text='Used for internal management. Not linked to permissions rules.', null=True, on_delete=django.db.models.deletion.CASCADE, to='hms.ManagementAreaCategory'),
        ),
    ]