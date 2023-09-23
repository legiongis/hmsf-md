import time
import json
import logging
from datetime import datetime
from django.http import Http404
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User, Group
import django.contrib.auth.password_validation as validation
from django.shortcuts import render, redirect
from django.utils.translation import ugettext as _
from django.urls import reverse
from arches.app.models.system_settings import settings
from arches.app.models.models import Node, GraphModel
from arches.app.models.tile import Tile
from arches.app.models.resource import Resource

from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.utils.forms import ArchesUserProfileForm
from arches.app.utils.response import JSONResponse
from arches.app.utils.permission_backend import user_is_resource_reviewer

from arches.app.views.user import UserManagerView

from fpan.search.components.rule_filter import RuleFilter
from hms.permissions_backend import (
    user_is_land_manager,
    user_is_scout,
)
from hms.views import scouts_dropdown

logger = logging.getLogger(__name__)

class FPANUserManagerView(UserManagerView):

    def get_hms_details(self, user):

        start = time.time()

        # get rule for Archaeological Site resource model
        graphid = str(GraphModel.objects.get(name="Archaeological Site").pk)
        rule = RuleFilter().compile_rules(user, graphids=[graphid], single=True)
        sites = RuleFilter().get_resources_from_rule(rule)

        site_lookup = {}
        for i in sites:
            i["scout_report_ct"] = 0
            i["scout_reports"] = []
            site_lookup[i["resourceinstanceid"]] = i

        siteid_node = Node.objects.get(name="FMSF Site ID", graph__name="Scout Report")
        siteid_nodeid = str(siteid_node.pk)
        rep_datas = Tile.objects.filter(nodegroup=siteid_node.nodegroup).values("data", "resourceinstance_id")

        # iterate the report data objects and if they match sites in the lookup,
        # add the report ids to that site object
        for rd in rep_datas:
            report_id = rd['resourceinstance_id']
            try:
                fmsfid = rd["data"][siteid_nodeid][0]["resourceId"]
            except IndexError as e:
                logger.debug(f"{report_id} - Scout Report has no FMSF Site ID")
                continue
            except KeyError as e:
                logger.debug(f"{report_id} - KeyError: {e}")
                continue
            if fmsfid in site_lookup:
                site_lookup[fmsfid]["scout_report_ct"] += 1
                res = Resource.objects.get(pk=report_id)
                site_lookup[fmsfid]["scout_reports"].append({
                    "displayname": res.displayname,
                    "url": reverse("resource_report", args=(report_id,)),
                })

        
        site_info = sorted(site_lookup.values(), key=lambda k: k["displayname"])
        logger.debug(f"getting hms_details for {user.username}: {time.time()-start} seconds elapsed")

        all_info = {
            "site_access_rules": rule.serialize(), 
            "accessible_sites": site_info,
        }
        return all_info

    def get(self, request):

        if self.request.user.is_authenticated and self.request.user.username != "anonymous":
            context = self.get_context_data(main_script="views/user-profile-manager", )

            title = "User Home"
            if request.user.is_superuser:
                title = "Admin: " + request.user.username
            elif user_is_land_manager(request.user):
                title = "Land Manager: " + request.user.username
            elif user_is_scout(request.user):
                title = "Scout: " + request.user.username

            context["nav"]["icon"] = "fa fa-user"
            context["nav"]["title"] = title
            context["nav"]["login"] = True
            context["nav"]["help"] = {
                "title": _("Profile Editing"),
                "template": "profile-manager-help",
            }
            context["validation_help"] = validation.password_validators_help_texts()

            ## retain this user_details acquisition as it pulls upstream Arches information.
            ## make sure it is all passed to the context variable as below.
            user_details = self.get_user_details(request.user)
            context["user_surveys"] = JSONSerializer().serialize(user_details["user_surveys"], sort_keys=False)
            context["identities"] = JSONSerializer().serialize(user_details["identities"], sort_keys=False)
            context["resources"] = JSONSerializer().serialize(user_details["resources"], sort_keys=False, exclude=["is_editable"])

            ## new, additional call to local method to get more HMS info
            hms_details = self.get_hms_details(request.user)
            context["site_access_rules"] = hms_details['site_access_rules']
            context["accessible_sites"] = hms_details['accessible_sites']

            if request.user.is_superuser:
                scouts_unsorted = json.loads(scouts_dropdown(request).content)
                context["scout_list"] = sorted(scouts_unsorted, key=lambda k: k['username'])

            return render(request, "views/user-profile-manager.htm", context)

        else:
            return redirect("/auth/")

    def post(self, request):

        if self.action == "get_user_names":
            data = {}
            if self.request.user.is_authenticated and user_is_resource_reviewer(request.user):
                userids = json.loads(request.POST.get("userids", "[]"))
                data = {u.id: u.username for u in User.objects.filter(id__in=userids)}
                return JSONResponse(data)

        if self.request.user.is_authenticated and self.request.user.username != "anonymous":

            context = self.get_context_data(main_script="views/user-profile-manager", )
            context["errors"] = []
            context["nav"]["icon"] = "fa fa-user"
            context["nav"]["title"] = _("Profile Manager")
            context["nav"]["login"] = True
            context["nav"]["help"] = {
                "title": _("Profile Editing"),
                "template": "profile-manager-help",
            }
            context["validation_help"] = validation.password_validators_help_texts()

            # retain this user_details acquisition as it pulls upstream Arches information.
            # make sure it is all passed to the context variable as below.
            user_details = self.get_user_details(request.user)
            context["user_surveys"] = JSONSerializer().serialize(user_details["user_surveys"])
            context["identities"] = JSONSerializer().serialize(user_details["identities"])
            context["resources"] = JSONSerializer().serialize(user_details["resources"])

            user_info = request.POST.copy()
            user_info["id"] = request.user.id
            user_info["username"] = request.user.username
            user_info["password1"] = request.user.password
            user_info["password2"] = request.user.password

            form = ArchesUserProfileForm(user_info)

            if form.is_valid():
                user = form.save()
                try:
                    admin_info = settings.ADMINS[0][1] if settings.ADMINS else ""
                    message = _(
                        "Your HMS profile was just changed.  If this was unexpected, please contact your Arches administrator at %s."
                        % (admin_info)
                    )
                    user.email_user(_("Your HMS profile has changed"), message)
                except Exception as e:
                    logger.error(e)
                request.user = user
            context["form"] = form

            ## new, additional call to local method to get more HMS info
            hms_details = self.get_hms_details(request.user)
            context["site_access_rules"] = hms_details['site_access_rules']
            context["accessible_sites"] = hms_details['accessible_sites']

            if request.user.is_superuser:
                scouts_unsorted = json.loads(scouts_dropdown(request).content)
                context["scout_list"] = sorted(scouts_unsorted, key=lambda k: k['username'])

            return render(request, "views/user-profile-manager.htm", context)
