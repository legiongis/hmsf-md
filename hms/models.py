from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from fpan.models.region import Region
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.
class Scout(User):
    middle_initial = models.CharField(max_length=1)


class ScoutProfile(models.Model):
    SITE_INTEREST_CHOICES = (
        ('Prehistoric', 'Prehistoric'),
        ('Historic', 'Historic'),
        ('Cemeteries', 'Cemeteries'),
        ('Underwater', 'Underwater'),
        ('Other', 'Other'),)

    user = models.OneToOneField(Scout, on_delete=models.CASCADE)
    street_address = models.CharField(max_length=30)
    city = models.CharField(max_length=30)
    state = models.CharField(max_length=30, default='Florida')
    zip_code = models.CharField(max_length=5)
    phone = models.CharField(max_length=12)
    background = models.TextField(
        "Please let us know a little about your education and occupation.")
    relevant_experience = models.TextField(
        "Please let us know about any relevant experience.")
    interest_reason = models.TextField(
        "Why are you interested in becoming a Heritage Monitoring Scout?")
    site_interest_type = models.CharField(
            "What type of sites are you interested in?",
            max_length=30,
            choices=SITE_INTEREST_CHOICES)
    region_choices = models.ManyToManyField(Region)
    # region_choices = models.CharField(
    #         "Which region(s) are you interested in monitoring sites in?",
    #         max_length=2,
    #         choices=REGION_CHOICES)
    ethics_agreement = models.BooleanField(default=False)


@receiver(post_save, sender=Scout)
def create_user_scout(sender, instance, created, **kwargs):
    if created:
        ScoutProfile.objects.create(user=instance)
    instance.scoutprofile.save()

@receiver(post_save, sender=Scout)
def save_user_scout(sender, instance, **kwargs):
    instance.scoutprofile.save()
