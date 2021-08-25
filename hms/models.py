from __future__ import unicode_literals

import time
import json
import logging
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
from arches.app.models.models import Node
from arches.app.models.tile import Tile

from fpan.search.components.site_filter import (
    SiteFilter,
    generate_no_access_filter,
    generate_attribute_filter,
    generate_geo_filter,
    generate_full_access_filter,
    generate_resourceid_filter,
)

logger = logging.getLogger("fpan")

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

def report_filter_from_site_filter(site_filter):
    """
    Utility function that returns a resourceid filter that contains all
    resourceids for Scout Reports attached to Archaeological Sites
    that fit the specified archaeological site filter.
    """
    start = time.time()
    if site_filter["access_level"] == "full_access":
        return generate_full_access_filter("Scout Report")
    if site_filter["access_level"] == "no_access":
        return generate_no_access_filter("Scout Report")

    resids = SiteFilter().get_resource_list_from_es_query(site_filter, ids_only=True)

    start = time.time()
    siteid_node = Node.objects.get(name="FMSF Site ID", graph__name="Scout Report")
    siteid_nodeid = str(siteid_node.pk)
    rep_datas = Tile.objects.filter(nodegroup=siteid_node.nodegroup).values("data", "resourceinstance_id")

    reportids = []
    for rd in rep_datas:
        try:
            fmsfid = rd["data"][siteid_nodeid][0]["resourceId"]
        except IndexError as e:
            pass
        if fmsfid in resids:
            reportids.append(str(rd["resourceinstance_id"]))

    report_filter = generate_resourceid_filter(resourceids=reportids)
    logger.debug(f"report_filter_from_site_filter: {time.time() - start}")
    return report_filter


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
    street_address = models.CharField(
        max_length=30,
        blank=True, null=True,
    )
    city = models.CharField(
        max_length=30,
        blank=True, null=True,
    )
    state = models.CharField(
        max_length=30,
        blank=True, null=True,
    )
    zip_code = models.CharField(
        max_length=5,
        blank=True, null=True,
    )
    phone = models.CharField(
        max_length=12,
        blank=True, null=True,
    )
    background = models.TextField(
        "Please let us know a little about your education and occupation.",
        blank=True, null=True,
    )
    relevant_experience = models.TextField(
        "Please let us know about any relevant experience.",
        blank=True, null=True,
    )
    interest_reason = models.TextField(
        "Why are you interested in becoming a Heritage Monitoring Scout?",
        blank=True, null=True,
    )
    site_interest_type = ArrayField(models.CharField(
        max_length=30,
        blank=True,
        choices=SITE_INTEREST_CHOICES),
        default=list
    )
    region_choices = models.ManyToManyField(Region)
    ethics_agreement = models.BooleanField(default=True)

    def __unicode__(self):
        return self.user.username

    def regions(self):
        return self.region_choices

    def get_graph_filter(self, graph_name):

        if graph_name == "Archaeological Site":
            if self.site_access_mode == "FULL":
                rule = generate_full_access_filter(graph_name)
            else:
                rule = generate_attribute_filter(
                    graph_name="Archaeological Site",
                    node_name="Assigned To",
                    value=self.user.username
                )

        elif graph_name == "Scout Report":
            ## This is identical to the analogous section of LandManager.get_graph_filter()
            arch_rule = self.get_graph_filter("Archaeological Site")
            rule = report_filter_from_site_filter(arch_rule)

        else:
            rule = generate_full_access_filter(graph_name)

        # print(rule)
        return rule

    def get_allowed_resources(self, graph_name, ids_only=False):
        """
        !! Currently ScoutProfile and LandManager have this identical method !!
        Based on the rule generated by self.get_graph_filter(), retrieve a list of
        resourceids that the user has access to for the specified graph. If user has
        full or no access to resources, an empty list will be returned.
        """

        rule = self.get_graph_filter(graph_name)
        if rule["access_level"] in ["full_access", "no_access"]:
            return []

        return SiteFilter().get_resource_list_from_es_query(rule, ids_only=ids_only)

    def site_access_rules_formatted(self):
        content = {}
        content["Archaeological Site"] = self.get_graph_filter("Archaeological Site")
        content["Scout Report"] = self.get_graph_filter("Scout Report")
        return format_json_display(content)

    site_access_rules_formatted.short_description = 'Derived Access Rules'

    def accessible_sites_formatted(self):
        return format_json_display(self.get_allowed_resources("Archaeological Site"))

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
    # and it is set during save() from self.user.username
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

    def get_graph_filter(self, graph_name):

        if graph_name == "Archaeological Site":
            if self.site_access_mode == "FULL":
                rule = generate_full_access_filter(graph_name)

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
                rule = generate_attribute_filter(
                    graph_name="Archaeological Site",
                    node_name="Management Area",
                    value=value
                )

            elif self.site_access_mode == "AGENCY":

                value = ["<no agency set>"]
                if self.management_agency:
                    value = [self.management_agency.name]

                rule = generate_attribute_filter(
                    graph_name="Archaeological Site",
                    node_name="Management Agency",
                    value=value
                )
            elif self.site_access_mode == "NONE":
                rule = generate_no_access_filter(graph_name)
            else:
                rule = generate_no_access_filter(graph_name)

        elif graph_name == "Scout Report":

            arch_rule = self.get_graph_filter("Archaeological Site")
            rule = report_filter_from_site_filter(arch_rule)

        else:
            rule = generate_full_access_filter(graph_name)

        return rule
    
    def get_allowed_resources(self, graph_name, ids_only=False):
        """
        !! Currently ScoutProfile and LandManager have this identical method !!
        Based on the rule generated by self.get_graph_filter(), retrieve a list of
        resourceids that the user has access to for the specified graph. If user has
        full or no access to resources, an empty list will be returned.
        """
        start = time.time()
        rule = self.get_graph_filter(graph_name)
        if rule["access_level"] in ["full_access", "no_access"]:
            return []
        id_list = SiteFilter().get_resource_list_from_es_query(rule, ids_only=ids_only)
        logger.debug(f"get_allowed_resources: {time.time()-start}")
        return id_list

    def site_access_rules_formatted(self):
        content = {}
        content["Archaeological Site"] = self.get_graph_filter("Archaeological Site")
        content["Scout Report"] = self.get_graph_filter("Scout Report")
        return format_json_display(content)

    site_access_rules_formatted.short_description = 'Derived Access Rules'

    def accessible_sites_formatted(self):
        return format_json_display(self.get_allowed_resources("Archaeological Site"))

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
