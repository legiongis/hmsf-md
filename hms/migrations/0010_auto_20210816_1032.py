# Generated by Django 2.2.13 on 2021-08-16 10:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hms', '0009_change_landmanager_access_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='scoutprofile',
            name='site_access_mode',
            field=models.CharField(choices=[('USERNAME=ASSIGNEDTO', 'USERNAME=ASSIGNEDTO'), ('FULL', 'FULL')], default='USERNAME=ASSIGNEDTO', help_text='<strong>USERNAME=ASSIGNEDTO</strong> sites to which the scout has been assigned<br><strong>FULL</strong> all sites', max_length=20),
        ),
        migrations.AlterField(
            model_name='landmanager',
            name='site_access_mode',
            field=models.CharField(blank=True, choices=[('NONE', 'NONE'), ('AREA', 'AREA'), ('AGENCY', 'AGENCY'), ('FULL', 'FULL')], default='NONE', help_text="<strong>NONE</strong> no access<br><strong>AREA</strong> sites within specified areas or grouped areas<br><strong>AGENCY</strong> sites managed by land manager's agency<br><strong>FULL</strong> all sites", max_length=20, null=True),
        ),
    ]