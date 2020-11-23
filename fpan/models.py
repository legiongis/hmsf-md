from django.contrib.gis.db import models


class Region(models.Model):
    name = models.CharField(max_length=254)
    region_code = models.CharField(max_length=4)
    geom = models.MultiPolygonField()

    # Returns the string representation of the model.
    def __str__(self):              # __unicode__ on Python 2
        return self.name

from django.contrib.gis.db import models

class ManagedArea(models.Model):
    """this model functions similar to the Region model. it should be moved to a new file
    or something... preferably Region and MananagedArea would be just put in models.py
    to improve the clarity of import statements, etc."""

    AGENCY_CHOICES = (
        ("FL Dept. of Environmental Protection, Div. of Recreation and Parks","FL Dept. of Environmental Protection, Div. of Recreation and Parks"),
        ("FL Dept. of Agriculture and Consumer Services, Florida Forest Service","FL Dept. of Agriculture and Consumer Services, Florida Forest Service"),
        ("FL Fish and Wildlife Conservation Commission","FL Fish and Wildlife Conservation Commission"),
        ("FL Dept. of Environmental Protection, Florida Coastal Office","FL Dept. of Environmental Protection, Florida Coastal Office"),
        ("FL Dept. of Environmental Protection, Office of Water Policy","FL Dept. of Environmental Protection, Office of Water Policy"),
    )

    CATEGORY_CHOICES = (
        ("State Park","State Park"),
        ("State Forest","State Forest"),
        ("Fish and Wildlife Conservation Commission","Fish and Wildlife Conservation Commission"),
        ("Aquatic Preserve","Aquatic Preserve"),
        ("Water Management District","Water Management District"),
    )

    WMD_DISTRICT_CHOICES = (
        ("North","North"),
        ("North Central","North Central"),
        ("West","West"),
        ("South","South"),
        ("Southwest","Southwest"),
        ("South Central","South Central"),
    )

    name = models.CharField(max_length=254)
    agency = models.CharField(max_length=254,choices=AGENCY_CHOICES)
    category = models.CharField(max_length=254,choices=CATEGORY_CHOICES)
    nickname = models.CharField(max_length=30,null=True,blank=True)
    sp_district = models.IntegerField(null=True, blank=True)
    wmd_district = models.CharField(max_length=20,choices=WMD_DISTRICT_CHOICES,null=True,blank=True)
    geom = models.MultiPolygonField()

    # Returns the string representation of the model.
    def __str__(self):              # __unicode__ on Python 2
        return self.name
