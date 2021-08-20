import json
from datetime import datetime
from django.http import Http404
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User, Group
import django.contrib.auth.password_validation as validation
from django.shortcuts import render
from django.utils.translation import ugettext as _
from arches.app.models.system_settings import settings
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.utils.forms import ArchesUserProfileForm
from arches.app.utils.response import JSONResponse
from arches.app.utils.permission_backend import user_is_resource_reviewer

from arches.app.views.user import UserManagerView

from fpan.search.components.site_filter import SiteFilter


class FPANUserManagerView(UserManagerView):

    def get_hms_details(self, user):

        # get rule for Archaeological Site resource model
        rule = SiteFilter().compile_rules(user, graph="f212980f-d534-11e7-8ca8-94659cf754d0")

        return rule

    def get(self, request):

        if self.request.user.is_authenticated and self.request.user.username != "anonymous":
            context = self.get_context_data(main_script="views/user-profile-manager", )

            context["nav"]["icon"] = "fa fa-user"
            context["nav"]["title"] = _("Profile Manager")
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
            context["site_access"] = hms_details

            return render(request, "views/user-profile-manager.htm", context)
        
        else:
            raise Http404("not found")

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

            ## retain this user_details acquisition as it pulls upstream Arches information.
            ## make sure it is all passed to the context variable as below.
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
                        "Your arches profile was just changed.  If this was unexpected, please contact your Arches administrator at %s."
                        % (admin_info)
                    )
                    user.email_user(_("You're Arches Profile Has Changed"), message)
                except Exception as e:
                    print(e)
                request.user = user
            context["form"] = form

            return render(request, "views/user-profile-manager.htm", context)
