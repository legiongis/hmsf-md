from __future__ import unicode_literals

import json
from uuid import uuid4
import logging
from typing_extensions import TypeAlias
from typing import List, TYPE_CHECKING, Tuple, Iterable
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers.data import JsonLexer

from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.contrib.gis.geos import MultiPolygon
from django.utils.safestring import mark_safe, SafeText
from django.db import connection

from arches.app.models.models import (
    Concept,
    Value,
    Relation,
)
from arches.app.models.concept import Concept as ConceptProxy

from hms.permissions_backend import (
    get_rule_by_graph,
    get_user_allowed_resources_by_graph,
)

if TYPE_CHECKING:
    pass

ManagementAgencyAlias: TypeAlias = "ManagementAgency"
FPANRegionAlias: TypeAlias = "FPANRegion"
ManagementAreaAlias: TypeAlias = "ManagementArea"
ManagementAreaGroupAlias: TypeAlias = "ManagementAreaGroup"

logger = logging.getLogger("fpan")


def format_json_display(data) -> SafeText:
    """very nice from here:
    https://www.laurencegellert.com/2018/09/django-tricks-for-processing-and-storing-json/"""

    content = json.dumps(data, indent=2)

    # format it with pygments and highlight it
    formatter = HtmlFormatter(style="colorful")
    response = highlight(content, JsonLexer(), formatter)

    # include the style sheet
    style = "<style>" + formatter.get_style_defs() + "</style><br/>"

    return mark_safe(style + response)


class Scout(User):
    middle_initial = models.CharField(max_length=1)

    if TYPE_CHECKING:
        scoutprofile: "ScoutProfile"

    class Meta:
        verbose_name = "Scout"
        verbose_name_plural = "Scouts"

    def serialize(self):

        serialized = {
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "street_address": self.scoutprofile.street_address,
            "city": self.scoutprofile.city,
            "state": self.scoutprofile.state,
            "zip_code": self.scoutprofile.zip_code,
            "phone": self.scoutprofile.phone,
            "background": self.scoutprofile.background,
            "relevant_experience": self.scoutprofile.relevant_experience,
            "interest_reason": self.scoutprofile.interest_reason,
            "site_interest_type": ";".join(self.scoutprofile.site_interest_type)
            if self.scoutprofile.site_interest_type
            else [],
            "fpan_regions2": ";".join(
                [r.name for r in self.scoutprofile.fpan_regions2.all()]
            ),
            "date_joined": self.date_joined.strftime("%Y-%m-%d"),
        }

        return serialized


SITE_INTEREST_CHOICES = (
    ("Prehistoric", "Prehistoric"),
    ("Historic", "Historic"),
    ("Cemeteries", "Cemeteries"),
    ("Underwater", "Underwater"),
    ("Other", "Other"),
)


class ScoutProfile(models.Model):
    ACCESS_MODE_CHOICES = [
        ("USERNAME=ASSIGNEDTO", "USERNAME=ASSIGNEDTO"),
        ("FULL", "FULL"),
    ]
    ACCESS_MODE_HELP_SCOUT = (
        "<strong>USERNAME=ASSIGNEDTO</strong> sites "
        "to which the scout has been assigned<br>"
        "<strong>FULL</strong> all sites"
    )

    user = models.OneToOneField(Scout, on_delete=models.CASCADE)
    site_access_mode = models.CharField(
        max_length=20,
        choices=ACCESS_MODE_CHOICES,
        default="USERNAME=ASSIGNEDTO",
        help_text=ACCESS_MODE_HELP_SCOUT,
    )
    street_address = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )
    city = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )
    state = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )
    zip_code = models.CharField(
        max_length=5,
        blank=True,
        null=True,
    )
    phone = models.CharField(
        max_length=12,
        blank=True,
        null=True,
    )
    background = models.TextField(
        "Please let us know a little about your education and occupation.",
        blank=True,
        null=True,
    )
    relevant_experience = models.TextField(
        "Please let us know about any relevant experience.",
        blank=True,
        null=True,
    )
    interest_reason = models.TextField(
        "Why are you interested in becoming a Heritage Monitoring Scout?",
        blank=True,
        null=True,
    )
    site_interest_type = ArrayField(
        models.CharField(max_length=30, blank=True, choices=SITE_INTEREST_CHOICES),
        default=list,
        null=True,
        blank=True,
    )
    fpan_regions2 = models.ManyToManyField(
        FPANRegionAlias,
        verbose_name="FPAN Regions",
    )
    ethics_agreement = models.BooleanField(default=True)

    def __unicode__(self):
        return self.user.username

    def site_access_rules_formatted(self) -> SafeText:
        content = {}
        content["Archaeological Site"] = get_rule_by_graph(
            self, graph_name="Archaeological Site"
        ).serialize()
        content["Scout Report"] = get_rule_by_graph(
            self, graph_name="Scout Report"
        ).serialize()
        return format_json_display(content)

    site_access_rules_formatted.short_description = "Derived Access Rules"  # type: ignore

    def accessible_sites_formatted(self):
        res = get_user_allowed_resources_by_graph(
            self, graph_name="Archaeological Site"
        )
        return format_json_display(res)

    accessible_sites_formatted.short_description = "Accessible Sites"  # type: ignore


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
    ACCESS_MODE_HELP_TEXT = (
        "<strong>NONE</strong> no access<br>"
        "<strong>AREA</strong> sites within specified areas or grouped areas<br>"
        "<strong>AGENCY</strong> sites managed by land manager's agency<br>"
        "<strong>FULL</strong> all sites"
    )

    user = models.OneToOneField(
        User, related_name="landmanager", on_delete=models.CASCADE
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
        ManagementAgencyAlias, null=True, blank=True, on_delete=models.CASCADE
    )
    individual_areas = models.ManyToManyField(ManagementAreaAlias, blank=True)
    grouped_areas = models.ManyToManyField(ManagementAreaGroupAlias, blank=True)

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

    def site_access_rules_formatted(self) -> SafeText:
        content = {}
        content["Archaeological Site"] = get_rule_by_graph(
            self, graph_name="Archaeological Site"
        ).serialize()
        content["Scout Report"] = get_rule_by_graph(
            self, graph_name="Scout Report"
        ).serialize()
        return format_json_display(content)

    site_access_rules_formatted.short_description = "Derived Access Rules"  # type: ignore

    def accessible_sites_formatted(self):
        res = get_user_allowed_resources_by_graph(
            self, graph_name="Archaeological Site"
        )
        return format_json_display(res)

    accessible_sites_formatted.short_description = "Accessible Sites"  # type: ignore


def get_collection_values(collection_name: str) -> Iterable[Tuple[(str, str)]]:

    collection = Value.objects.get(
        value=collection_name, concept__nodetype__nodetype="Collection"
    ).concept
    concept_ids = Relation.objects.filter(
        conceptfrom=collection, relationtype_id="member"
    ).values_list("conceptto", flat=True)
    return Value.objects.filter(concept_id__in=concept_ids).values_list("value", "pk")


def get_or_create_concept(label, parent_lbl, collection_lbl, concept_id=None):
    """Helper function that creates a new concept and adds it to the specified
    parent and collection."""

    topconcept = Value.objects.get(
        value=parent_lbl, concept__nodetype__nodetype="Concept"
    ).concept
    collection = Value.objects.get(
        value=collection_lbl, concept__nodetype__nodetype="Collection"
    ).concept

    ## first check if this concept already exists. It must be under the specified
    ## top concept (parent label) and also under the provided collection
    for val in Value.objects.filter(
        valuetype_id="prefLabel",
        value=label,
        language_id="en",
    ):
        if val.concept:
            if Relation.objects.filter(
                conceptfrom=topconcept,
                conceptto=val.concept,
                relationtype_id="narrower",
            ).exists():
                if Relation.objects.filter(
                    conceptfrom=collection,
                    conceptto=val.concept,
                    relationtype_id="member",
                ).exists():
                    return val.concept

    if not concept_id:
        concept_id = str(uuid4())

    concept = Concept.objects.create(
        conceptid=concept_id,
        nodetype_id="Concept",
        legacyoid=f"{settings.ARCHES_NAMESPACE_FOR_DATA_EXPORT.rstrip('/')}/rdm/{concept_id}",
    )
    Value.objects.create(
        concept=concept,
        valuetype_id="prefLabel",
        value=label,
        language_id="en",
    )

    Relation.objects.create(
        conceptfrom=topconcept,
        conceptto=concept,
        relationtype_id="narrower",
    )

    Relation.objects.create(
        conceptfrom=collection,
        conceptto=concept,
        relationtype_id="member",
    )

    # need to reinstantiate this concept with the "proxy" class to index it
    cp = ConceptProxy().get(concept_id)
    cp.index()

    return concept


def get_concept_value_id(concept):
    try:
        return str(
            Value.objects.get(
                concept=concept,
                language_id="en",
                valuetype_id="prefLabel",
            ).pk
        )
    except Value.DoesNotExist:
        return None


class ManagementAgency(models.Model):
    class Meta:
        verbose_name = "Management Agency"
        verbose_name_plural = "Management Agencies"

    code = models.CharField(primary_key=True, max_length=20)
    name = models.CharField(null=True, blank=True, max_length=200)
    concept = models.ForeignKey(
        Concept,
        null=True,
        blank=True,
        limit_choices_to={"nodetype_id": "Concept"},
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return self.name if self.name else f"ManagementAgency {self.pk}"

    def serialize(self):

        return {
            "id": self.code,
            "name": self.name,
        }

    @property
    def concept_value_id(self):
        return get_concept_value_id(self.concept)

    def save(self, *args, **kwargs):

        if self.pk and not self.concept:
            self.concept = get_or_create_concept(
                f"{self.name} ({self.pk})",
                parent_lbl="Management Agencies",
                collection_lbl="Management Agencies",
            )

        return super(ManagementAgency, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.concept:
            self.concept.delete()
        return super(ManagementAgency, self).delete(*args, **kwargs)


class ManagementAreaCategory(models.Model):
    class Meta:
        verbose_name = "Management Area Category"
        verbose_name_plural = "Management Area Categories"

    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


MANAGEMENT_LEVELS = (
    ("Federal", "Federal"),
    ("State", "State"),
    ("County", "County"),
    ("City", "City"),
)


class ManagementArea(models.Model):
    class Meta:
        verbose_name = "Management Area"
        verbose_name_plural = "Management Areas"

    name = models.CharField(max_length=254)
    display_name = models.CharField(max_length=254, null=True, blank=True)
    category = models.ForeignKey(
        ManagementAreaCategory,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Used for internal management. Not linked to permissions rules.",
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
        help_text="Used to grant access to Land Managers whose accounts have "
        "the Agency Filter applied.",
    )
    management_level = models.CharField(
        max_length=25,
        choices=MANAGEMENT_LEVELS,
        null=True,
        blank=True,
        help_text="Used for internal management. Not linked to permissions rules.",
    )
    nickname = models.CharField(max_length=30, null=True, blank=True)
    load_id = models.CharField(max_length=200, null=True, blank=True)
    geom = models.MultiPolygonField()
    concept = models.ForeignKey(
        Concept,
        null=True,
        blank=True,
        limit_choices_to={"nodetype_id": "Concept"},
        on_delete=models.CASCADE,
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

    def get_intersecting_resource_ids(self) -> List[str]:
        if self.geom:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT resourceinstanceid FROM geojson_geometries
                            WHERE ST_Intersects(
                                ST_GeomFromText( %s, 4326 ),
                                ST_Transform(geojson_geometries.geom, 4326)
                            );""",
                    (self.geom.wkt,),
                )
                rows = cursor.fetchall()
            return [str(i[0]) for i in rows if len(i) > 0]
        else:
            return []

    def save(self, *args, **kwargs):

        if self.management_agency:
            self.display_name = (
                f"{self.name} | {self.category} | {self.management_agency.name}"
            )
        elif self.category:
            self.display_name = f"{self.name} | {self.category}"
        else:
            self.display_name = self.name

        if self.pk and not self.concept:
            concept_label = f"{self.name} ({self.pk})"
            concept = get_or_create_concept(
                concept_label,
                parent_lbl="Management Areas",
                collection_lbl="Management Areas",
            )
            self.concept = concept

        return super(ManagementArea, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.concept:
            self.concept.delete()
        return super(ManagementArea, self).delete(*args, **kwargs)


class ManagementAreaGroup(models.Model):
    class Meta:
        verbose_name = "Management Area Group"
        verbose_name_plural = "Management Area Groups"

    name = models.CharField(max_length=100)
    areas = models.ManyToManyField(ManagementArea)
    note = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name


class FPANRegion(models.Model):
    class Meta:
        verbose_name = "FPAN Region"
        verbose_name_plural = "FPAN Regions"

    name = models.CharField(max_length=100)
    geom = models.MultiPolygonField()

    def __str__(self):
        return self.name if self.name else f"FPAN Region ({self.pk})"
