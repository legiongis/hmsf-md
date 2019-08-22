import json
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.http import HttpResponse, Http404 
from django.core.urlresolvers import reverse
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.utils.translation import ugettext as _
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string, get_template

from arches.app.models import models
from arches.app.models.system_settings import settings
from arches.app.models.resource import Resource
from arches.app.models.tile import Tile
from arches.app.models.graph import Graph
from arches.app.models.card import Card
from arches.app.utils.JSONResponse import JSONResponse
from arches.app.utils.betterJSONSerializer import JSONSerializer, JSONDeserializer
from arches.app.views.resource import ResourceReportView

from fpan.utils.tokens import account_activation_token
from fpan.utils.accounts import check_anonymous, check_duplicate_username, check_state_access, check_scout_access
from fpan.models import Region

from hms.models import Scout, ScoutProfile
from hms.views import scouts_dropdown
from hms.forms import ScoutForm, ScoutProfileForm


def index(request):
    scout_form = ScoutForm()
    return render(request, 'index.htm', {
        'main_script': 'index',
        'active_page': 'Home',
        'app_title': '{0} | HMS'.format(settings.APP_NAME),
        'copyright_text': settings.COPYRIGHT_TEXT,
        'copyright_year': settings.COPYRIGHT_YEAR,
        'scout_form': scout_form,
        'page':'index'
    })
    
# @user_passes_test(check_anonymous)
def hms_home(request):
    if request.method == "POST":
        scout_profile_form = ScoutProfileForm(
            request.POST,
            instance=request.user.scout.scoutprofile)
        if scout_profile_form.is_valid():
            scout_profile_form.save()
            messages.add_message(request, messages.INFO, 'Your profile has been updated.')
        else:
            messages.add_message(request, messages.ERROR, 'Form was invalid.')
        
        return render(request, "home-hms.htm", {
            'scout_profile': scout_profile_form,
            'page':'home-hms'})
        
    else:
        scout_profile_form = None
        try:
            scout_profile_form = ScoutProfileForm(instance=request.user.scout.scoutprofile)
        except Scout.DoesNotExist:
            pass

    return render(request, "home-hms.htm", {
        'scout_profile': scout_profile_form,
        'page':'home-hms'})
        
@user_passes_test(check_anonymous)
def scout_profile(request):
    if request.method == "POST":
        scout_profile_form = ScoutProfileForm(
            request.POST,
            instance=request.user.scout.scoutprofile)
        if scout_profile_form.is_valid():
            scout_profile_form.save()
            messages.add_message(request, messages.INFO, 'Your profile has been updated.')
        else:
            messages.add_message(request, messages.ERROR, 'Form was invalid.')

    else:
        scout_profile_form = ScoutProfileForm(instance=request.user.scout.scoutprofile)

    return render(request, "fpan/scout-profile.htm", {
        'scout_profile': scout_profile_form})

@user_passes_test(check_state_access)
def state_home(request):
    return render(request, 'home-state.htm', {'page':'home-state'})

@never_cache
def auth(request,login_type):

    if not login_type in ['hms','state','logout']:
        raise Http404("not found")
        
    if login_type == 'logout':
        logout(request)
        return redirect('fpan_home')

    auth_attempt_success = None
    
    # POST request is taken to mean user is logging in
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None and user.is_active:
            if login_type == "hms":
                if check_scout_access(user) or user.is_superuser:
                    login(request, user)
                    auth_attempt_success = True
                else:
                    auth_attempt_success = False
            elif login_type == "state":
                if check_state_access(user):
                    login(request, user)
                    auth_attempt_success = True
                else:
                    auth_attempt_success = False
            user.password = ''
        else:
            auth_attempt_success = False

    next = request.GET.get('next', reverse('home'))
    if auth_attempt_success:
        if user.is_superuser:
            return redirect('search_home')
        if login_type == "hms":
            return redirect('hms_home')
        if login_type == "state":
            return redirect('state_home')
        return redirect(next)
    else:
        return render(request, 'login.htm', {
            'app_name': settings.APP_NAME,
            'auth_failed': (auth_attempt_success is not None),
            'next': next,
            'login_type':login_type,
            'page':'login',
        })

@never_cache
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, _('Your password has been updated'))
            if check_state_access(user):
                return redirect('state_home')
            if check_scout_access(user):
                return redirect('hms_home')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change-password.htm', {
        'form': form,
        'page':'change-password'
    })

def scout_signup(request):
    if request.method == "POST":
        form = ScoutForm(request.POST)
        if form.is_valid():
            firstname = form.cleaned_data.get('first_name')
            middleinitial = form.cleaned_data.get('middle_initial')
            lastname = form.cleaned_data.get('last_name')
            user = form.save(commit=False)
            user.is_active = False
            user.username = check_duplicate_username(
                firstname[0].lower() 
                + middleinitial.lower() 
                + lastname.lower())

            user.save()
            current_site = get_current_site(request)
            msg_vars = {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            }
            message_txt = render_to_string('email/account_activation_email.htm', msg_vars)
            message_html = render_to_string('email/account_activation_email_html.htm', msg_vars)
            subject_line = settings.EMAIL_SUBJECT_PREFIX + 'Activate your account.'
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = form.cleaned_data.get('email')
            email = EmailMultiAlternatives(subject_line,message_txt,from_email,to=[to_email])
            email.attach_alternative(message_html, "text/html")
            email.send()            
            return render(request,'email/please-confirm.htm')
    else:
        form = ScoutForm()

    return render(request, 'index.htm', {'scout_form': form})

def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = Scout.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, Scout.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        user = authenticate(username=user.username, password=user.password)
        scout_form = ScoutForm(instance=user)
        scout_profile_form = ScoutProfileForm()
        return redirect('auth',login_type='hms')
    else:
        return HttpResponse('Activation link is invalid!')

def show_regions(request):
    regions = Region.objects.all()
    return JSONResponse(regions)

def server_error(request, template_name='500.html'):
    from django.template import RequestContext
    from django.http import HttpResponseServerError
    t = get_template(template_name)
    return HttpResponseServerError(t.render(RequestContext(request)))
    
@user_passes_test(lambda u: u.is_superuser)
def fpan_dashboard(request):
    scouts_unsorted = json.loads(scouts_dropdown(request).content)
    scouts = sorted(scouts_unsorted, key=lambda k: k['username']) 
    return render(request,'fpan-dashboard.htm',context={'scouts':scouts})


class FPANResourceReportView(ResourceReportView):


    def get_inline_resources(self, graph, resourceid):

        inline_config = settings.REPORT_INLINES
        inline_output = []

        if graph.name in inline_config:

            # per resource model, there may be multiple inline defined
            model_level_data = {
                "graph_name": graph.name,
                "inlines": []
            }

            # iterate the inlines defined for this resource model, and collect
            # all of the resources that match it.
            for inline_info in inline_config[graph.name]:

                # ultimately, for each inline there will be a node name and a list of resources
                collected_data = {
                    "node_name": inline_info['node_to_look_in'],
                }

                # the graph of the resource model that stores the resource-instance node information
                # that may match this resource's resource id
                inline_model = Graph.objects.get(name=inline_info['inline_model'])

                # the specific node that holds the resource instance data. this must be a resource-instance node.
                inline_node = models.Node.objects.get(graph=inline_model, name=inline_info['node_to_look_in'])

                # the nodegroup for the node defined above. this is needed because tiles have nodegroupids,
                # not node ids (though the node ids are in the tile.data.keys())
                inline_ng = models.NodeGroup.objects.get(nodegroupid=inline_node.nodegroup_id)

                # get all tiles matching the nodegroupd
                inline_tiles = Tile.objects.filter(nodegroup=inline_ng)

                # for all of the tiles, if the this resource's resourceinstanceid is in the tile.data.values(),
                # then add the resourceinstance_id of the tile that contains this value.
                inline_resids = [str(t.resourceinstance_id) for t in inline_tiles if resourceid in t.data.values()]

                # get the list of resources, both the resourceinstanceid and display name for each
                resources = list()
                for resid in inline_resids:
                    res = Resource.objects.get(resourceinstanceid=resid)
                    resources.append({"resid": resid, "displayname": res.displayname})

                # sort the resources by name and add them to the collected data object
                collected_data['resources'] = sorted(resources, key=lambda k: k['displayname'])
                model_level_data['inlines'].append(collected_data)

            inline_output.append(model_level_data)

        return inline_output

    def get(self, request, resourceid=None):

        print "this is the new FPAN view"
        # manually update the settings here
        # before adding this line, the mapbox key was not available in the report, for example.
        settings.update_from_db()

        lang = request.GET.get('lang', settings.LANGUAGE_CODE)
        resource = Resource.objects.get(pk=resourceid)
        displayname = resource.displayname
        resource_models = models.GraphModel.objects.filter(isresource=True).exclude(
            isactive=False).exclude(pk=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)

        tiles = Tile.objects.filter(resourceinstance=resource).order_by('sortorder')

        graph = Graph.objects.get(graphid=resource.graph_id)
        cards = Card.objects.filter(graph=graph).order_by('sortorder')
        permitted_cards = []
        permitted_tiles = []

        perm = 'read_nodegroup'

        inlines = self.get_inline_resources(graph, resourceid)

        for card in cards:
            if request.user.has_perm(perm, card.nodegroup):
                card.filter_by_perm(request.user, perm)
                permitted_cards.append(card)

        for tile in tiles:
            if request.user.has_perm(perm, tile.nodegroup):
                tile.filter_by_perm(request.user, perm)
                permitted_tiles.append(tile)


        try:
            map_layers = models.MapLayer.objects.all()
            map_markers = models.MapMarker.objects.all()
            map_sources = models.MapSource.objects.all()
            geocoding_providers = models.Geocoder.objects.all()
        except AttributeError:
            raise Http404(_("No active report template is available for this resource."))

        cardwidgets = [widget for widgets in [card.cardxnodexwidget_set.order_by(
            'sortorder').all() for card in permitted_cards] for widget in widgets]

        datatypes = models.DDataType.objects.all()
        widgets = models.Widget.objects.all()
        templates = models.ReportTemplate.objects.all()
        card_components = models.CardComponent.objects.all()

        context = self.get_context_data(
            main_script='views/resource/report',
            report_templates=templates,
            templates_json=JSONSerializer().serialize(templates, sort_keys=False, exclude=['name', 'description']),
            card_components=card_components,
            card_components_json=JSONSerializer().serialize(card_components),
            cardwidgets=JSONSerializer().serialize(cardwidgets),
            tiles=JSONSerializer().serialize(permitted_tiles, sort_keys=False),
            cards=JSONSerializer().serialize(permitted_cards, sort_keys=False, exclude=[
                'is_editable', 'description', 'instructions', 'helpenabled', 'helptext', 'helptitle', 'ontologyproperty']),
            datatypes_json=JSONSerializer().serialize(
                datatypes, exclude=['modulename', 'issearchable', 'configcomponent', 'configname', 'iconclass']),
            geocoding_providers=geocoding_providers,
            inline_data=inlines,
            widgets=widgets,
            map_layers=map_layers,
            map_markers=map_markers,
            map_sources=map_sources,
            graph_id=graph.graphid,
            graph_name=graph.name,
            graph_json=JSONSerializer().serialize(graph, sort_keys=False, exclude=[
                'functions', 'relatable_resource_model_ids', 'domain_connections', 'edges', 'is_editable', 'description', 'iconclass', 'subtitle', 'author']),
            resourceid=resourceid,
            displayname=displayname,
        )

        if graph.iconclass:
            context['nav']['icon'] = graph.iconclass
        context['nav']['title'] = graph.name
        context['nav']['res_edit'] = True
        context['nav']['print'] = True
        context['nav']['print'] = True

        return render(request, 'views/resource/report.htm', context)
