from __future__ import unicode_literals

import json
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers.data import JsonLexer

from django.contrib.gis.db import models
from django.contrib.auth.models import User, Group
from fpan.models import Region
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.fields import ArrayField
from django.contrib.gis.geos import MultiPolygon
from django.utils.safestring import mark_safe

from arches.app.models.resource import Resource
from arches.app.models.graph import Graph

from fpan.search.components.site_filter import (
    SiteFilter,
    generate_no_access_filter,
    generate_attribute_filter,
    generate_geo_filter,
    generate_full_access_filter,
)

def format_json_display(data):
    """very nice from here:
    https://www.laurencegellert.com/2018/09/django-tricks-for-processing-and-storing-json/"""

    content = json.dumps(data, indent=2)

    # format it with pygments and highlight it
    formatter = HtmlFormatter(style='colorful')
    response = highlight(content, JsonLexer(), formatter)

        # include the style sheet
    style = "<style>" + formatter.get_style_defs() + "</style><br/>"

    return mark_safe(style + response)

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

    ACCESS_MODE_CHOICES = [
        ("USERNAME=ASSIGNEDTO", "USERNAME=ASSIGNEDTO"),
        ("FULL", "FULL"),
    ]
    ACCESS_MODE_HELP_SCOUT = "<strong>USERNAME=ASSIGNEDTO</strong> sites "\
        "to which the scout has been assigned<br>"\
        "<strong>FULL</strong> all sites"

    user = models.OneToOneField(Scout, on_delete=models.CASCADE)
    site_access_mode = models.CharField(
        max_length=20,
        choices=ACCESS_MODE_CHOICES,
        default="USERNAME=ASSIGNEDTO",
        help_text=ACCESS_MODE_HELP_SCOUT,
    )
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

    @property
    def site_access_rules(self):

        rules = {}
        if self.site_access_mode == "FULL":
            rules["Archaeological Site"] = generate_full_access_filter()
        else:
            rules["Archaeological Site"] = generate_attribute_filter(
                graph_name="Archaeological Site",
                node_name="Assigned To",
                value=self.user.username
            )
        return rules

    @property
    def accessible_sites(self):
        graphid = str(Graph.objects.get(name="Archaeological Site").graphid)
        arch_rules = self.site_access_rules["Archaeological Site"]
        resids = SiteFilter().get_resource_list_from_es_query(arch_rules, graphid)
        return resids

    def site_access_rules_formatted(self):
        return format_json_display(self.site_access_rules)

    site_access_rules_formatted.short_description = 'Derived Access Rules'

    def accessible_sites_formatted(self):
        return format_json_display(self.accessible_sites)

    accessible_sites_formatted.short_description = 'Accessible Sites'


@receiver(post_save, sender=Scout)
def create_user_scout(sender, instance, created, **kwargs):
    if created:
        ScoutProfile.objects.create(user=instance)
    # group = Group.objects.get(name='Scout')
    # group.user_set.add(instance)
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
    
    ACCESS_MODE_CHOICES = [
        ("NONE", "NONE"),
        ("AREA", "AREA"),
        ("AGENCY", "AGENCY"),
        ("FULL", "FULL"),
    ]
    ACCESS_MODE_HELP_TEXT = "<strong>NONE</strong> no access<br>"\
        "<strong>AREA</strong> sites within specified areas or grouped areas<br>"\
        "<strong>AGENCY</strong> sites managed by land manager's agency<br>"\
        "<strong>FULL</strong> all sites"

    user = models.OneToOneField(
        User,
        related_name="landmanager",
        on_delete=models.CASCADE
    )
    # this username field is only here to allow search within the admin interface
    username = models.CharField(
        null=True,
        blank=True,
        max_length=200,
        editable=False,
    )
    site_access_mode = models.CharField(
        max_length=20,
        choices=ACCESS_MODE_CHOICES,
        default="NONE",
        help_text=ACCESS_MODE_HELP_TEXT,
        blank=True,
        null=True,
    )
    management_agency = models.ForeignKey(
        "ManagementAgency",
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    individual_areas = models.ManyToManyField("ManagementArea", blank=True)
    grouped_areas = models.ManyToManyField("ManagementAreaGroup", blank=True)

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        self.username = self.user.username
        super(LandManager, self).save(*args, **kwargs)

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
    def accessible_sites(self):
        graphid = str(Graph.objects.get(name="Archaeological Site").graphid)
        arch_rules = self.site_access_rules["Archaeological Site"]
        resids = SiteFilter().get_resource_list_from_es_query(arch_rules, graphid)
        return resids

    @property
    def filter_rules(self):

        rules = {"access_level": "", "":""}

    @property
    def site_access_rules(self):

        rules = {}

        if self.site_access_mode == "FULL":
            rules["Archaeological Site"] = generate_full_access_filter()

        elif self.site_access_mode == "AREA":
            ## this was supposed to be a proper geo_filter as below, but
            ## that doesn't allow for arbitrary assignment of nearby
            ## management areas that don't spatially intersect.
            # multipolygon = user.landmanager.areas_as_multipolygon
            # rules["Archaeological Site"] = generate_geo_filter(
            #   graph_name="Archaeological Site"
            #   geometry=multipolygon,
            # )

            ## instead, apply attribute filter based on the names of
            ## of associated areas.
            value = ["<no area set>"]
            if len(self.all_areas) > 0:
                value = [i.name for i in self.all_areas]
            rules["Archaeological Site"] = generate_attribute_filter(
                graph_name="Archaeological Site",
                node_name="Management Area",
                value=value
            )

        elif self.site_access_mode == "AGENCY":

            value = ["<no agency set>"]
            if self.management_agency:
                value = [self.management_agency.name]

            rules["Archaeological Site"] = generate_attribute_filter(
                graph_name="Archaeological Site",
                node_name="Management Agency",
                value=value
            )
        elif self.site_access_mode == "NONE":
            rules["Archaeological Site"] = generate_no_access_filter()
        else:
            rules["Archaeological Site"] = generate_no_access_filter()

        return rules

    def set_allowed_resources(self):
        """very confusingly, this method must be called from admin.LandManagerAdmin.save_related().
        This is because self.save() and post_save here do not yet have the updated versions
        of the ManyToManyFields (individual_areas and grouped_areas)"""

        from hms.utils import update_hms_permissions_table
        update_hms_permissions_table(user=self.user)

    def site_access_rules_formatted(self):
        return format_json_display(self.site_access_rules)

    site_access_rules_formatted.short_description = 'Derived Access Rules'

    def accessible_sites_formatted(self):
        return format_json_display(self.accessible_sites)

    accessible_sites_formatted.short_description = 'Accessible Sites'


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
        if self.display_name:
            return self.display_name
        elif self.name:
            return self.name
        else:
            return super(ManagementArea, self).__str__()


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
