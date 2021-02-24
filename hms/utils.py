from django.contrib.auth.models import User
from arches.app.models.resource import Resource
from arches.app.models.models import GraphModel

from fpan.search.components.site_filter import SiteFilter
from .models import UserXResourceInstanceAccess

def update_hms_permissions_table(user=None):

    all_resource_graphids = (
        GraphModel.objects.filter(isresource=True, isactive=True)
        .exclude(name="Arches System Settings")
    ).values_list('graphid', flat=True)
    graphids = [str(i) for i in all_resource_graphids]

    if user is None:
        users = User.objects.all()
    else:
        users = [user]

    for user in users:
        all_resources = []
        for graphid in graphids:
            try:
                res_access = SiteFilter().get_allowed_resource_ids(user, graphid)
            except:
                print("--- ERROR ---", user)
                continue
            all_resources += res_access.get("id_list", [])

        for resourceid in all_resources:
            res = Resource.objects.get(pk=resourceid)
            obj, created = UserXResourceInstanceAccess.objects.get_or_create(
                user=user,
                resource=res
            )

        for entry in UserXResourceInstanceAccess.objects.filter(user=user):
            if not str(entry.resource.resourceinstanceid) in all_resources:
                entry.delete()

def get_resource_instance_access(user, graphid):

    rules = SiteFilter().get_rules(user, graphid)
    if rules["access_level"] in ["full_access", "no_access"]:
        return rules
    else:
        ok = UserXResourceInstanceAccess.objects.filter(
            user=user,
            resource__graph_id=graphid,
        )
        rules["id_list"] = [str(i.resource.resourceinstanceid) for i in ok]
    return rules

def user_can_access_resource(user, resourceid):

    res = Resource.objects.get(pk=resourceid)
    access = get_resource_instance_access(user, str(res.graph.graphid))
    if access["access_level"] == "full_access":
        return True
    elif access["access_level"] == "no_access":
        return False
    else:
        return resourceid in access["id_list"]
