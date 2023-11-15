from __future__ import unicode_literals

import time
import json
from uuid import uuid4
import logging
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers.data import JsonLexer

from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.fields import ArrayField
from django.contrib.gis.geos import MultiPolygon
from django.utils.safestring import mark_safe

from arches.app.models.resource import Resource
from arches.app.models.models import (
    Node, Concept, Value, Relation,
)
from arches.app.models.tile import Tile
from arches.app.models.concept import Concept as ConceptProxy

from fpan.search.components.rule_filter import RuleFilter, Rule

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

def report_rule_from_arch_rule(arch_rule):
    """
    Utility function that returns a resourceid filter that contains all
    resourceids for Scout Reports attached to Archaeological Sites
    that fit the specified archaeological site filter.
    """
    start = time.time()
    if arch_rule.type == "full_access":
        return Rule("full_access", graph_name="Scout Report")
    elif arch_rule.type == "no_access":
        arch_ids = []
    else:
        ## get ids only for the sites this user has access to
        arch_ids = RuleFilter().get_resources_from_rule(arch_rule, ids_only=True)

    ## now add all ids for all Historic Cemeteries and Historic Structures
    cem_ids = list(Resource.objects.filter(graph__name="Historic Cemetery").values_list("pk", flat=True))
    struct_ids = list(Resource.objects.filter(graph__name="Historic Structure").values_list("pk", flat=True))

    resids = [str(i) for i in arch_ids+cem_ids+struct_ids]

    siteid_node = Node.objects.get(name="FMSF Site ID", graph__name="Scout Report")
    siteid_nodeid = str(siteid_node.pk)
    rep_datas = Tile.objects.filter(nodegroup=siteid_node.nodegroup).values("data", "resourceinstance_id")
    reportids = []
    for rd in rep_datas:
        try:
            fmsfid = rd["data"][siteid_nodeid][0]["resourceId"]
            if fmsfid in resids:
                reportids.append(str(rd["resourceinstance_id"]))
        except (IndexError, KeyError, TypeError) as e:
            logger.warn(f"can't get fmsf id from {rd['resourceinstance_id']}")
            logger.warn(e)
        except Exception as e:
            logger.error(f"can't get fmsf id from {rd['resourceinstance_id']}")
            logger.error(e)

    report_rule = Rule("resourceid_filter", resourceids=reportids)
    logger.debug(f"report_rule_from_arch_rule: {time.time() - start}")
    return report_rule


class Scout(User):
    middle_initial = models.CharField(max_length=1)

    class Meta:
        verbose_name = "Scout"
        verbose_name_plural = "Scouts"

    def serialize(self):

        serialized = {
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'street_address': self.scoutprofile.street_address,
            'city': self.scoutprofile.city,
            'state': self.scoutprofile.state,
            'zip_code': self.scoutprofile.zip_code,
            'phone': self.scoutprofile.phone,
            'background': self.scoutprofile.background,
            'relevant_experience': self.scoutprofile.relevant_experience,
            'interest_reason': self.scoutprofile.interest_reason,
            'site_interest_type': ";".join(self.scoutprofile.site_interest_type),
            'fpan_regions': ";".join([r.name for r in self.scoutprofile.fpan_regions.all()]),
            'date_joined': self.date_joined.strftime("%Y-%m-%d"),
        }

        return serialized

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
        default=list,
        null=True,
        blank=True,
    )
    fpan_regions = models.ManyToManyField(
        "ManagementArea",
        verbose_name="FPAN Regions",
        limit_choices_to={
            'category__name': "FPAN Region"
        },
    )
    ethics_agreement = models.BooleanField(default=True)

    def __unicode__(self):
        return self.user.username

    def get_graph_rule(self, graph_name):

        if graph_name == "Archaeological Site":
            if self.site_access_mode == "FULL":
                rule = Rule("full_access", graph_name=graph_name)
            else:
                rule = Rule("attribute_filter",
                    graph_name="Archaeological Site",
                    node_id=settings.SPATIAL_JOIN_GRAPHID_LOOKUP['Archaeological Site']['Assigned To'],
                    value=[self.user.username]
                )

        elif graph_name == "Scout Report":
            ## This is identical to the analogous section of LandManager.get_graph_rule()
            arch_rule = self.get_graph_rule("Archaeological Site")
            rule = report_rule_from_arch_rule(arch_rule)

        else:
            rule = Rule("full_access", graph_name=graph_name)

        return rule

    def get_allowed_resources(self, graph_name, ids_only=False):
        """
        !! Currently ScoutProfile and LandManager have this identical method !!
        Based on the rule generated by self.get_graph_rule(), retrieve a list of
        resourceids that the user has access to for the specified graph. If user has
        full or no access to resources, an empty list will be returned.
        """

        rule = self.get_graph_rule(graph_name)
        if rule.type in ["full_access", "no_access"]:
            return []

        return RuleFilter().get_resources_from_rule(rule, ids_only=ids_only)

    def site_access_rules_formatted(self):
        content = {}
        content["Archaeological Site"] = self.get_graph_rule("Archaeological Site").serialize()
        content["Scout Report"] = self.get_graph_rule("Scout Report").serialize()
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

    def get_graph_rule(self, graph_name):

        if graph_name == "Archaeological Site":
            if self.site_access_mode == "FULL":
                rule = Rule("full_access", graph_name=graph_name)

            elif self.site_access_mode == "AREA":
                ## this was supposed to be a proper geo rule as below, but
                ## that doesn't allow for arbitrary assignment of nearby
                ## management areas that don't spatially intersect.
                # multipolygon = user.landmanager.areas_as_multipolygon
                # rules["Archaeological Site"] = Rule(
                #   graph_name="Archaeological Site"
                #   geometry=multipolygon,
                # )

                ## instead, apply attribute rule based on the names of
                ## of associated areas.
                value = ["<no area set>"]
                if len(self.all_areas) > 0:
                    value = [i.name for i in self.all_areas]
                rule = Rule("attribute_filter",
                    graph_name="Archaeological Site",
                    node_id=settings.SPATIAL_JOIN_GRAPHID_LOOKUP['Archaeological Site']["Management Area"],
                    value=value
                )

            elif self.site_access_mode == "AGENCY":

                value = ["<no agency set>"]
                if self.management_agency:
                    value = [self.management_agency.name]

                rule = Rule("attribute_filter",
                    graph_name="Archaeological Site",
                    node_id=settings.SPATIAL_JOIN_GRAPHID_LOOKUP['Archaeological Site']["Management Agency"],
                    value=value
                )
            elif self.site_access_mode == "NONE":
                rule = Rule("no_access", graph_name=graph_name)
            else:
                rule = Rule("no_access", graph_name=graph_name)

        elif graph_name == "Scout Report":

            arch_rule = self.get_graph_rule("Archaeological Site")
            rule = report_rule_from_arch_rule(arch_rule)

        else:
            rule = Rule("full_access", graph_name=graph_name)

        return rule
    
    def get_allowed_resources(self, graph_name, ids_only=False):
        """
        !! Currently ScoutProfile and LandManager have this identical method !!
        Based on the rule generated by self.get_graph_rule(), retrieve a list of
        resourceids that the user has access to for the specified graph. If user has
        full or no access to resources, an empty list will be returned.
        """
        start = time.time()
        rule = self.get_graph_rule(graph_name)
        if rule.type in ["full_access", "no_access"]:
            return []
        id_list = RuleFilter().get_resources_from_rule(rule, ids_only=ids_only)
        logger.debug(f"get_allowed_resources: {time.time()-start}")
        return id_list

    def site_access_rules_formatted(self):
        content = {}
        content["Archaeological Site"] = self.get_graph_rule("Archaeological Site").serialize()
        content["Scout Report"] = self.get_graph_rule("Scout Report").serialize()
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


def create_new_concept(label, parent_lbl, collection_lbl, concept_id=None):
    """ Helper function that creates a new concept and adds it to the specified
    parent and collection. """

    if not concept_id:
        concept_id = str(uuid4())

    concept = Concept.objects.create(
        conceptid=concept_id,
        nodetype_id="Concept",
        legacyoid=f"{settings.ARCHES_NAMESPACE_FOR_DATA_EXPORT.rstrip('/')}/rdm/{concept_id}",
    )
    v = Value.objects.create(
        concept=concept,
        valuetype_id="prefLabel",
        value=label,
        language_id="en",
    )

    p = Value.objects.get(value=parent_lbl, concept__nodetype__nodetype="Concept").concept
    rp = Relation.objects.create(
        conceptfrom=p,
        conceptto=concept,
        relationtype_id="narrower",
    )

    c = Value.objects.get(value=collection_lbl, concept__nodetype__nodetype="Collection").concept
    rc = Relation.objects.create(
        conceptfrom=c,
        conceptto=concept,
        relationtype_id="member",
    )

    # need to reinstantiate this concept with the "proxy" class to index it
    cp = ConceptProxy().get(concept_id)
    cp.index()

    return concept

def get_concept_value_id(concept):
    try:
        return str(Value.objects.get(
            concept=concept,
            language_id="en",
            valuetype_id="prefLabel",
        ).pk)
    except Value.DoesNotExist:
        return None


class ManagementAgency(models.Model):

    class Meta:
        verbose_name = "Management Agency"
        verbose_name_plural = "Management Agencies"

    code = models.CharField(
        primary_key=True,
        max_length=20
    )
    name = models.CharField(null=True, blank=True, max_length=200)
    concept = models.ForeignKey(Concept, null=True, blank=True,
        limit_choices_to={"nodetype_id": "Concept"},
        on_delete=models.CASCADE
    )

    def __str__(self):
        return self.name

    def serialize(self):

        return {
            'id': self.code,
            'name': self.name,
        }

    @property
    def concept_value_id(self):
        return get_concept_value_id(self.concept)

    def save(self, *args, **kwargs):

        if not self.concept:
            concept = create_new_concept(
                self.name,
                parent_lbl="Management Agencies",
                collection_lbl="Management Agencies"
            )
            self.concept = concept

        super(ManagementAgency, self).save(*args, **kwargs)

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
    concept = models.ForeignKey(Concept, null=True, blank=True,
        limit_choices_to={"nodetype_id": "Concept"},
        on_delete=models.CASCADE
    )

    def __str__(self):
        if self.display_name:
            return self.display_name
        elif self.name:
            return self.name
        else:
            return super(ManagementArea, self).__str__()

    @property
    def concept_value_id(self):
        return get_concept_value_id(self.concept)

    def set_concept(self):

        if self.category.name == "FPAN Region":
            concept = create_new_concept(
                self.name,
                parent_lbl="FPAN Regions",
                collection_lbl="FPAN Regions"
            )
        elif self.category.name == "County":
            concept = create_new_concept(
                self.name,
                parent_lbl="Counties",
                collection_lbl="Counties"
            )
        else:
            concept = create_new_concept(
                self.display_name,
                parent_lbl="Management Areas",
                collection_lbl="Management Areas"
            )
        self.concept = concept

    def save(self, *args, **kwargs):

        if self.category and self.category.name == "FPAN Region":
            self.display_name = self.name.replace("FPAN ","")
        elif self.management_agency:
            self.display_name = f"{self.name} | {self.category} | {self.management_agency.name}"
        elif self.category:
            self.display_name = f"{self.name} | {self.category}"
        else:
            self.display_name = self.name

        if not self.concept:
            self.set_concept()
        else:
            self.update_concept

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
