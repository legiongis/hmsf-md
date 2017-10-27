#from django.db import models
from django.contrib.gis.db import models
# from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import User

class ScoutProfile(models.Model):
    REGION_CHOICES = (
        ('NW', 'Northwest'),
        ('NC', 'North Central'),
        ('NE', 'Northeast'),
        ('CR', 'Central'),
        ('WC', 'West Central'),
        ('SW', 'Southwest'),
        ('SE', 'Southeast'),)

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
    region_choices = models.CharField(
            "Which region(s) are you interested in monitoring sites in?",
            max_length=2,
            choices=REGION_CHOICES)
    ethics_agreement = models.BooleanField()


# class Region(models.Model):
#     region = models.CharField(max_length=254)
#     geom = models.MultiPolygonField(srid=4362)

# # Auto-generated `LayerMapping` dictionary for Region model
# region_mapping = {
#     'region' : 'REGION',
#     'geom' : 'MULTIPOLYGON',
# }
