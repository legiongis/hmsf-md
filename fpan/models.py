import time
import logging
from django.contrib.gis.db import models
from django.contrib.auth.models import User
from django.urls import reverse

from arches.app.models.models import Node
from arches.app.models.resource import Resource
from arches.app.models.tile import Tile

from fpan.utils import get_node_value

logger = logging.getLogger(__name__)

## this model will be deprecated in favor of ManagementArea and ManagementAreaGroup
class Region(models.Model):
    name = models.CharField(max_length=254)
    region_code = models.CharField(max_length=4)
    geom = models.MultiPolygonField()

    # Returns the string representation of the model.
    def __str__(self):              # __unicode__ on Python 2
        return self.name

from django.contrib.gis.db import models

## this model will be deprecated in favor of ManagementArea and ManagementAreaGroup
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


class FMSFResource(object):

    def __init__(self, resourceid):

        self.resource = Resource.objects.get(pk=resourceid)
        self.type = self.resource.graph.name
        self.id = str(self.resource.pk)
        self.scout_reports = self.get_reports()
        self.display_name = self.set_display_name()
        self.link = self.set_link()
        self.assigned_to = self.set_assigned_to()

    def get_reports(self):
        start = time.time()
        if self.resource.graph.name == "Scout Report":
            return None

        siteid_node = Node.objects.get(name="FMSF Site ID", graph__name="Scout Report")
        t_datas = Tile.objects.filter(nodegroup=siteid_node.nodegroup).values("data", "resourceinstance_id")

        reports = []
        for content in t_datas:
            # this is obtaining the resource id from the resource-instance-list node
            try:
                resid = content['data'][str(siteid_node.pk)][0]["resourceId"]
            except IndexError as e:
                logger.debug(f"{content['resourceinstance_id']} - Scout Report without FMSF Site ID")
                continue
            if resid == self.id:
                reports.append(ScoutReport(content['resourceinstance_id']))

        logger.debug(f"getting reports: {time.time() - start} seconds elapsed")

        return reports

    def set_display_name(self):

        if self.resource.graph.name == "Scout Report":
            d = get_node_value(self.resource, "Scout Visit Date")
            scouts = self.resource.get_node_values("Scout ID(s)")
            scoutnames = ", ".join([User.objects.get(pk=i).username for i in scouts])
            display_name = f"{d} - {scoutnames}"

        else:
            sitename = get_node_value(self.resource, "FMSF Name")
            siteid = get_node_value(self.resource, "FMSF ID")
            display_name = f"{siteid} - {sitename}"

        return display_name

    def set_link(self):
        return reverse("resource_report", args=(self.id,))

    def set_assigned_to(self):

        if self.type == "Archaeological Site":
            return get_node_value(self.resource, "Assigned To")
        else:
           return None

    def serialize(self):

        obj =  {
            "resourceid": self.id,
            "display_name": self.display_name,
            "type": self.type,
            "link": self.link,
            "assigned_to": self.assigned_to,
        }

        if self.type == "Scout Report":
            obj["fmsf_resourceid"] = str(self.fmsf_resource.pk)
        else:
            report_list = [i.serialize() for i in self.scout_reports]
            obj["scout_reports"] = sorted(report_list, key=lambda k: k['display_name']) 

        return obj


class ScoutReport(FMSFResource):

    def __init__(self, resourceid):

        super().__init__(resourceid)

        siteid_node = Node.objects.get(name="FMSF Site ID", graph__name="Scout Report")
        siteid = Tile.objects.get(
            resourceinstance_id=resourceid,
            nodegroup=siteid_node.nodegroup
        ).data[str(siteid_node.pk)][0]["resourceId"]
        fmsf_res = Resource.objects.get(pk=siteid)

        self.fmsf_resource = fmsf_res
