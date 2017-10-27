from django.contrib.gis.db import models
from .region import Region
from django.contrib.auth.models import User

class Scout(models.Model):

    SITE_INTEREST_CHOICES = (
        ('Prehistoric', 'Prehistoric'),
        ('Historic', 'Historic'),
        ('Cemeteries', 'Cemeteries'),
        ('Underwater', 'Underwater'),
        ('Other', 'Other'),)

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    street_address = models.CharField(max_length=30)
    city = models.CharField(max_length=30)
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
    ethics_agreement = models.BooleanField()
