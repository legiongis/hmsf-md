import csv
from io import BytesIO
import json
from pathlib import Path
import logging
from datetime import datetime
from typing import Tuple

from django.core.mail import EmailMultiAlternatives
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib.sites.shortcuts import get_current_site
from django.http import (
    HttpResponseServerError,
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotFound,
    FileResponse,
)
from django.shortcuts import render, redirect
from django.template import RequestContext
from django.template.loader import render_to_string, get_template
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.urls import reverse
from django.views.generic import View

from arches.app.views.api import APIBase
from arches.app.utils.response import JSONResponse
from arches.app.models.resource import Resource
from arches.app.models.system_settings import settings
from arches.app.views.user import UserManagerView

from fpan.decorators import user_is_scout_decorator
from hms.fmsf import FMSFResource
from hms.forms import ScoutForm, ScoutProfileForm
from hms.models import Scout, ScoutProfile
from hms.permissions_backend import user_is_land_manager, user_is_scout
from hms.utils import account_activation_token, create_scout_from_valid_form


logger = logging.getLogger(__name__)


def index(request):
    return render(
        request,
        "index.htm",
        {
            "main_script": "index",
            "active_page": "Home",
            "app_title": "{0} | Home".format(settings.APP_NAME),
            "page": "index",
        },
    )


def about(request):
    return render(
        request,
        "about.htm",
        {
            "main_script": "about",
            "active_page": "About",
            "app_title": "{0} | About the Database".format(settings.APP_NAME),
            "page": "about",
        },
    )


@method_decorator(user_is_scout_decorator, name="dispatch")
class ScoutProfileView(UserManagerView):
    def get(self, request):

        context = self.get_context_data()

        title = "User Home"
        if request.user.is_superuser:
            title = "Admin: " + request.user.username
        elif user_is_land_manager(request.user):
            title = "Land Manager: " + request.user.username
        elif user_is_scout(request.user):
            title = "Scout: " + request.user.username

        context["nav"]["icon"] = "fa fa-user"
        context["nav"]["title"] = title

        context["scout_profile"] = None
        context["page"] = "scout-profile"
        context["help"] = {
            "title": "Profile Editing",
            "template": "profile-manager-help",
        }

        try:
            context["scout_profile"] = ScoutProfileForm(
                instance=request.user.scout.scoutprofile
            )
        except Scout.DoesNotExist:
            pass
        return render(
            request,
            "scout-profile.htm",
            context,
        )

    def post(self, request):
        scout_profile_form = ScoutProfileForm(
            request.POST, instance=request.user.scout.scoutprofile
        )
        if scout_profile_form.is_valid():
            scout_profile_form.save()
            messages.add_message(
                request, messages.INFO, "Your profile has been updated."
            )
            return redirect(reverse("user_profile_manager"))
        else:
            messages.add_message(request, messages.ERROR, "Form was invalid.")
            context = self.get_context_data()
            title = "User Home"
            if request.user.is_superuser:
                title = "Admin: " + request.user.username
            elif user_is_land_manager(request.user):
                title = "Land Manager: " + request.user.username
            elif user_is_scout(request.user):
                title = "Scout: " + request.user.username

            context["nav"]["icon"] = "fa fa-user"
            context["nav"]["title"] = title

            context["scout_profile"] = scout_profile_form
            context["page"] = "scout-profile"
            context["help"] = {
                "title": "Profile Editing",
                "template": "profile-manager-help",
            }
            return render(
                request,
                "scout-profile.htm",
                context,
            )


def server_error(request, template_name="500.html"):

    t = get_template(template_name)
    return HttpResponseServerError(t.render(RequestContext(request).__dict__))


class LoginView(View):
    def get(self, request):

        login_type = request.GET.get("t", "landmanager")
        if request.GET.get("logout", None) is not None:
            try:
                user = request.user
            except Exception as e:
                logger.warning(e)
                return redirect("/")

            if user_is_scout(user):
                login_type = "scout"
            # send land managers and admin back to the landmanager login
            else:
                login_type = "landmanager"

            logger.info(
                f"logging out: {user.username} | redirect to /auth/ should follow"
            )
            logout(request)
            # need to redirect to 'auth' so that the user is set to anonymous via the middleware
            return redirect(f"/auth/?t={login_type}")
        else:
            next = request.GET.get("next", None)
            return render(
                request,
                "login.htm",
                {
                    "auth_failed": False,
                    "next": next,
                    "login_type": login_type,
                },
            )

    def post(self, request):
        # POST request is taken to mean user is logging in
        login_type = request.GET.get("t", "landmanager")
        next = request.GET.get("next", None)
        username = request.POST.get("username", None)
        password = request.POST.get("password", None)
        user = authenticate(username=username, password=password)

        if user is not None and user.is_active:
            auth_attempt_success = True
            # these conditionals ensure that scouts and land managers must
            # use the correct login portals
            if user_is_land_manager(user) and login_type != "landmanager":
                auth_attempt_success = False

            if user_is_scout(user) and login_type != "scout":
                auth_attempt_success = False

            # if user survives above checks, login
            if auth_attempt_success is True:
                login(request, user)
                user.password = ""

                # set next redirect if not previously set
                if next is None:
                    next = request.POST.get("next", reverse("user_profile_manager"))

                return redirect(next)

        return render(
            request,
            "login.htm",
            {"auth_failed": True, "next": next, "login_type": login_type},
            status=401,
        )


def login_patch(request, login_type):
    return redirect(f"/auth/?t={login_type}")


def activate_page(request, uidb64, token):

    return render(
        request,
        "hms/email/activation_page.htm",
        {
            "activation_link": f"/activate/?uidb64={uidb64}&token={token}",
        },
    )


def activate(request):

    uidb64 = request.GET.get("uidb64")
    token = request.GET.get("token")
    if all([uidb64, token]):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            logger.debug(f"activate user: {uid}")
            user = Scout.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, Scout.DoesNotExist) as e:
            logger.debug(f"error during account activation: {e}")
            return redirect("/auth/?t=scout")
        valid_token = account_activation_token.check_token(user, token)
        if not valid_token:
            logger.debug("token is invalid (user already activated??)")
        if user is not None and valid_token:
            user.is_active = True
            user.save()
            logger.debug(f"user set to active: {user}")
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect(reverse("user_profile_manager"))

    return redirect("/auth/?t=scout")


def scout_signup(request):

    context = {
        "main_script": "scout-signup",
        "active_page": "Scout Signup",
        "app_title": "{0} | Scout Signup".format(settings.APP_NAME),
        "scout_form": None,
        "page": "scout-signup",
    }

    if request.method == "GET":
        scout_form = ScoutForm()
        context["scout_form"] = scout_form
        return render(request, "scout-signup.htm", context)

    elif request.method == "POST":
        form = ScoutForm(request.POST)
        if form.is_valid():
            scout, encoded_uid, token = create_scout_from_valid_form(form)

            current_site = get_current_site(request)
            baseurl = f"http://{current_site.domain}"
            if settings.HTTPS:
                baseurl = f"https://{current_site.domain}"
            msg_vars = {
                "user": scout,
                "baseurl": baseurl,
                "uid": encoded_uid,
                "token": token,
            }
            message_txt = render_to_string(
                "hms/email/account_activation_email.htm", msg_vars
            )
            message_html = render_to_string(
                "hms/email/account_activation_email_html.htm", msg_vars
            )
            subject_line = settings.EMAIL_SUBJECT_PREFIX + "Activate your account."
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = form.cleaned_data.get("email")
            if to_email is not None:
                email = EmailMultiAlternatives(
                    subject_line, message_txt, from_email, to=[to_email]
                )
                email.attach_alternative(message_html, "text/html")
                email.send()
            return render(request, "hms/email/please-confirm.htm")

        context["scout_form"] = form
        return render(request, "scout-signup.htm", context)

    else:
        raise Http404


def scouts_dropdown(request):
    resourceid = request.GET.get("resourceid", None)

    matched_scouts = ScoutProfile.objects.all().prefetch_related("fpan_regions2")
    ## otherwise, get region for this resource, and only return scouts
    ## who are intersted in scouting in that region
    if resourceid:
        with open(Path(settings.APP_ROOT, "data", "county_lookup.json"), "r") as o:
            lookup = json.load(o)
        res = FMSFResource(resourceid)
        if res.siteid:
            entry = lookup.get(res.siteid[:2])
            matched_scouts = ScoutProfile.objects.filter(
                fpan_regions2__name__contains=entry["region"]
            ).distinct()

    # iterate scouts and create a list of objects to return for the dropdown
    return_scouts = []
    for scout in matched_scouts:
        display_name = scout.user.username
        if scout.site_interest_type:
            display_name += " | " + ", ".join(scout.site_interest_type)
        if scout.site_access_mode == "FULL":
            display_name += " | already has FULL access to sites"
        return_scouts.append(
            {
                "id": scout.user.pk,
                "username": {"en": {"value": scout.user.username, "direction": "ltr"}},
                "display_name": display_name,
                "site_interest_type": scout.site_interest_type,
                "fpan_regions": [region.name for region in scout.fpan_regions2.all()],
            }
        )

    return JSONResponse(
        sorted(return_scouts, key=lambda k: k["username"]["en"]["value"])
    )


@user_passes_test(lambda u: u.is_superuser)
def scout_list_download(request):

    csvname = datetime.now().strftime("HMS_all_scouts_%d-%m-%y.csv")

    # create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename={}".format(csvname)

    # the keys here must match those returned by the Scout().serialize() method
    field_mapping = {
        "username": "Scout ID",
        "first_name": "First Name",
        "last_name": "Last Name",
        "email": "Email",
        "street_address": "Street Address",
        "city": "City",
        "state": "State",
        "zip_code": "Zip Code",
        "phone": "Phone",
        "site_interest_type": "Site Types",
        "fpan_regions2": "Regions",
        "date_joined": "Signup Date",
        "background": "Education/Occupation",
        "relevant_experience": "Relevant Experience",
        "interest_reason": "Interest Reasons",
    }

    writer = csv.DictWriter(response, fieldnames=list(field_mapping.values()))
    writer.writeheader()
    for scout in Scout.objects.all():
        serialized = scout.serialize()
        translate_row = {field_mapping[k]: serialized[k] for k in serialized.keys()}
        writer.writerow(translate_row)

    return response


## TODO: Does this really need to inherit from APIBase?
class DownloadScoutReportPhotos(APIBase):
    def get(self, request):
        """
        Respond with a zip file of photos for a given Scout Report.
        """
        if not (reportid := request.GET.get("rid")):
            return HttpResponseBadRequest(b"Expected url param `rid` (resource id).")

        logger.info("Zipped photos were requested for scout report: " + reportid)

        try:
            zipfile_name, photos = zipped_photos(reportid)
            return FileResponse(
                photos,
                filename=zipfile_name,
                content_type="application/zip",
                as_attachment=True,
            )
        except ValueError as e:
            msg = e
            response = HttpResponseNotFound(msg)
        except OSError as e:
            msg = "Coudn't create the zip file: " + str(e)
            response = HttpResponseServerError(msg)
        except Exception as e:
            msg = (
                "An unexpected error occured when trying to create the zip file: "
                + str(e)
            )
            response = HttpResponseServerError(msg)

        logger.warning(msg)
        return response


def zipped_photos(reportid: str) -> Tuple[str, BytesIO]:
    """
    Returns a tuple containing:
        - zip file name
        - buffer containing a zip file of photos for the provided Scout Report

    Makes synchronous network calls to fetch files from S3.

    Raises:
        ValueError: If resource not found
        LookupError: If resource has no photos
        OSError: If there's an issue reading files or creating the zip
        FileNotFoundError: If a photo file doesn't exist in storage
        MemoryError: If files are too large to fit in memory
    """
    from zipfile import ZipFile
    from arches.app.models.models import File, Node
    from arches.app.models.tile import Tile

    report: Resource
    try:
        report = Resource.objects.get(pk=reportid)
    except Exception as e:
        raise ValueError(f"report not found: resource id: {reportid}: {e}") from e

    # NOTE: Must get photo ids from the tile data.
    # If we get all photo files associated with a resource,
    # we also get photos that were removed from the resource,
    # if they still exist in the `File` table and storage.

    # NOTE: Later, we might want additional tile data for:
    # - Including `Comment` and `Photo Type` node data in the output,
    #     e.g. to be included in a text file in the zipped photos.
    # - Using the display name (tile.photo.name), as opposed to file.path.name.
    #     which includes the true filename on disk/S3, and may differ from the
    #     display name when a file of the same name was previously uploaded.
    # In this case, we'd query the db for `Comment` and `Photo Type` `Nodes`,
    # and use those PKs to get the node data as in:
    # `tile.data.get(str(comment_node.pk))`

    photo_node = Node.objects.get(
        name="Photo", graph_id=settings.GRAPH_LOOKUP["sr"]["id"]
    )
    resource_photo_tiles = Tile.objects.filter(
        nodegroup=photo_node.nodegroup,
        resourceinstance=report,
    )
    curr_photo_file_ids = [
        photo["file_id"]
        for tile in resource_photo_tiles
        for photo in tile.data.get(str(photo_node.pk))
    ]
    curr_photo_files = File.objects.filter(pk__in=curr_photo_file_ids)

    if not curr_photo_files.exists():
        # should never see this
        # Save Images button only shows when report has photos
        raise LookupError(f"Report does not have photos. resource id: {reportid}")

    zip_buf = BytesIO()
    with ZipFile(zip_buf, "w") as zip_file:
        for f in curr_photo_files:
            with f.path.open("rb") as content:
                zip_file.writestr(f.path.name.split("/")[-1], content.read())
    zip_buf.seek(0)

    fmsf_site_id = ""

    fmsf_site_id_node = Node.objects.get(
        name="FMSF Site ID", graph_id=settings.GRAPH_LOOKUP["sr"]["id"]
    )
    fmsf_site_id_tiles = Tile.objects.filter(
        nodegroup=fmsf_site_id_node.nodegroup, resourceinstance=report
    )
    if fmsf_site_id_tiles.exists():
        # filter has results -> must be exactly 1, and the site must exist
        fmsf_site_resourceid = (
            fmsf_site_id_tiles[0]
            .data.get(str(fmsf_site_id_node.pk))[0]
            .get("resourceId")
        )
        # site display name = "{id} - {name}"
        fmsf_site_id = (
            Resource.objects.get(pk=fmsf_site_resourceid)
            .displayname()
            .split(" - ", maxsplit=1)[0]
            .strip()
        )

    # report display name = "{report date} - {author,author,...}"
    report_date, report_authors = report.displayname().split(" - ", maxsplit=1)
    report_date = report_date.strip()
    report_authors = "-".join(report_authors.split(","))

    _ = "_"
    zipfile_name = (
        f"photos{_}{fmsf_site_id}{_}{report_date}{_}{report_authors}.zip"
        if fmsf_site_id
        else f"photos{_}{report_date}{_}{report_authors}.zip"
    )

    return zipfile_name, zip_buf
