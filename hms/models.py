from __future__ import unicode_literals

from django.contrib.gis.db import models
from django.contrib.auth.models import User, Group
from fpan.models import Region
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.fields import ArrayField
from django.contrib.gis.geos import MultiPolygon

from arches.app.models.resource import Resource
from arches.app.models.models import GraphModel

class UserXResourceInstanceAccess(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
    )

# Create your models here.
class Scout(User):
    middle_initial = models.CharField(max_length=1)

    class Meta:
        verbose_name = "Scout"
        verbose_name_plural = "Scouts"

SITE_INTEREST_CHOICES = (
    ('Prehistoric', 'Prehistoric'),
    ('Historic', 'Historic'),
    ('Cemeteries', 'Cemeteries'),
    ('Underwater', 'Underwater'),
    ('Other', 'Other'),)

class ScoutProfile(models.Model):
    user = models.OneToOneField(Scout, on_delete=models.CASCADE)
    street_address = models.CharField(max_length=30)
    city = models.CharField(max_length=30)
    state = models.CharField(max_length=30, default='Florida')
    zip_code = models.CharField(max_length=5)
    phone = models.CharField(max_length=12)
    background = models.TextField(
        "Please let us know a little about your education and occupation.", blank=True)
    relevant_experience = models.TextField(
        "Please let us know about any relevant experience.", blank=True)
    interest_reason = models.TextField(
        "Why are you interested in becoming a Heritage Monitoring Scout?", blank=True)
    site_interest_type = ArrayField(models.CharField(
            max_length=30,
            blank=True,
            choices=SITE_INTEREST_CHOICES), default=list, blank=True)
    region_choices = models.ManyToManyField(Region)
    ethics_agreement = models.BooleanField(default=True)

    def __unicode__(self):
        return self.user.username

    def regions(self):
        return self.region_choices


@receiver(post_save, sender=Scout)
def create_user_scout(sender, instance, created, **kwargs):
    if created:
        ScoutProfile.objects.create(user=instance)
    group = Group.objects.get(name='Scout')
    group.user_set.add(instance)
    group_cs = Group.objects.get(name='Crowdsource Editor')
    group_cs.user_set.add(instance)
    group_cs = Group.objects.get(name='Resource Editor')
    group_cs.user_set.add(instance)
    instance.scoutprofile.save()

@receiver(post_save, sender=Scout)
def save_user_scout(sender, instance, **kwargs):
    instance.scoutprofile.save()

## DEPRECATED - Previously, this model was used in conjunction with
## LandManagerProfile, which has since been renamed LandManager. The change cut
## this intermediate model out of the mix, as it was ultimately not necessary.
# class LandManager(User):
#
#     class Meta:
#         verbose_name = "Land Manager"
#         verbose_name_plural = "Land Managers"
#
#     def __str__(self):
#         return self.username
#
#     def get_areas(self):
#         areas = self.landmanagerprofile.individual_areas.all()
#         for ga in self.landmanagerprofile.grouped_areas.all():
#             areas = areas.union(ga.areas.all())
#         return areas

class LandManager(models.Model):

    class Meta:
        verbose_name = "Land Manager"
        verbose_name_plural = "Land Managers"

    user = models.OneToOneField(
        User,
        related_name="landmanager",
        on_delete=models.CASCADE
    )
    management_agency = models.ForeignKey(
        "ManagementAgency",
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    full_access = models.BooleanField(
        default=False,
        help_text="Give this user access to all Archaeological Sites.",
    )
    apply_agency_filter = models.BooleanField(
        default=False,
        help_text="Give this user access to all Archaeological Sites managed"\
            "by their Agency (as defined above).",
        blank=True,
        null=True,
    )
    apply_area_filter = models.BooleanField(
        default=False,
        help_text="Give this user access to all Archaeological Sites within "\
            "any of the specified areas or groups of areas below.",
        blank=True,
        null=True,
    )
    individual_areas = models.ManyToManyField("ManagementArea", blank=True)
    grouped_areas = models.ManyToManyField("ManagementAreaGroup", blank=True)

    def __str__(self):
        return self.user.username

    @property
    def all_areas(self):
        areas = self.individual_areas.all()
        for ga in self.grouped_areas.all():
            areas = areas.union(ga.areas.all())
        return areas

    @property
    def areas_as_multipolygon(self):
        poly_agg = list()
        for area in self.all_areas:
            # each area is a MultiPolygon so iterate the Polygons within it
            for poly in area.geom:
                poly_agg.append(poly)
        full_multi = MultiPolygon(poly_agg, srid=4326)
        return full_multi

    @property
    def filter_rules(self):

        rules = {"access_level": "", "":""}

    def set_allowed_resources(self):
        """very confusingly, this method must be called from admin.LandManagerAdmin.save_related().
        This is because self.save() and post_save here do not yet have the updated versions
        of the ManyToManyFields (individual_areas and grouped_areas)"""

        from hms.utils import update_hms_permissions_table
        update_hms_permissions_table(user=self.user)


@receiver(post_save, sender=LandManager)
def create_user_land_manager(sender, instance, created, **kwargs):
    if created:
        group_cs = Group.objects.get(name='Crowdsource Editor')
        group_cs.user_set.add(instance.user)
        group_cs = Group.objects.get(name='Resource Editor')
        group_cs.user_set.add(instance.user)


## PROBLEM: these signals cause errors in the admin interface when createing
## new land managers or land manager profiles. The solution now is to comment
## them out and direct admins to create new profiles through the Land Manager
## Profile admin page, and also make the new Land Manager through that page
## at the same time.

# @receiver(post_save, sender=LandManager)
# def create_user_land_manager(sender, instance, created, **kwargs):
#     if created:
#         LandManagerProfile.objects.create(user=instance)

# @receiver(post_save, sender=LandManager)
# def save_user_land_manager(sender, instance, **kwargs):
#     instance.landmanagerprofile.save()


class ManagementAgency(models.Model):

    class Meta:
        verbose_name = "Management Agency"
        verbose_name_plural = "Management Agencies"

    code = models.CharField(
        primary_key=True,
        max_length=20
    )
    name = models.CharField(null=True, blank=True, max_length=200)

    def __str__(self):
        return self.name

    def serialize(self):

        return {
            'id': self.code,
            'name': self.name,
        }

class ManagementAreaCategory(models.Model):

    class Meta:
        verbose_name = "Management Area Category"
        verbose_name_plural = "Management Area Categories"

    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

MANAGEMENT_LEVELS = (
    ("Federal","Federal"),
    ("State","State"),
    ("County","County"),
    ("City","City"),
)

class ManagementArea(models.Model):

    class Meta:
        verbose_name = "Management Area"
        verbose_name_plural = "Management Areas"

    name = models.CharField(max_length=254)
    display_name = models.CharField(max_length=254,null=True,blank=True)
    category = models.ForeignKey(
        ManagementAreaCategory,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Used for internal management. Not linked to permissions rules."
    )
    description = models.CharField(
        max_length=254,
        null=True,
        blank=True,
    )
    management_agency = models.ForeignKey(
        ManagementAgency,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Used to grant access to Land Managers whose accounts have "\
        "the Agency Filter applied."
    )
    management_level = models.CharField(
        max_length=25,
        choices=MANAGEMENT_LEVELS,
        null=True,
        blank=True,
        help_text="Used for internal management. Not linked to permissions rules."
    )
    nickname = models.CharField(max_length=30,null=True,blank=True)
    load_id = models.CharField(max_length=200,null=True,blank=True)
    geom = models.MultiPolygonField()

    def __str__(self):
        return self.display_name


    def save(self, *args, **kwargs):

        if self.management_agency:
            self.display_name = f"{self.name} | {self.category} | {self.management_agency.name}"
        else:
            self.display_name = f"{self.name} | {self.category}"

        super(ManagementArea, self).save(*args, **kwargs)


class ManagementAreaGroup(models.Model):

    class Meta:
        verbose_name = "Management Area Group"
        verbose_name_plural = "Management Area Groups"

    name = models.CharField(max_length=100)
    areas = models.ManyToManyField(ManagementArea)
    note = models.CharField(max_length=255)

    def __str__(self):
        return self.name
