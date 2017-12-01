from django.shortcuts import render
from arches.app.utils.JSONResponse import JSONResponse
from .models import Scout, ScoutProfile
import json
from arches.app.models.resource import Resource
from arches.app.models.tile import Tile
from arches.app.models.models import Node, Value
from fpan.models import Region

def scouts_dropdown(request):
    resourceid = request.GET.get('resourceid', None)
    
    ## get all scouts right off the bat
    all_scouts = ScoutProfile.objects.all()
    return_scouts = []
    
    ## this should be improved with a big refactoring of this view. DRY...
    if not resourceid:
        for scout in all_scouts:
            display_name = scout.user.username + " | " + ", ".join(scout.site_interest_type)
            return_scouts.append({
                'id': scout.user_id,
                'username': scout.user.username,
                'display_name': display_name,
                'site_interest_type': scout.site_interest_type,
                'region_choices': [region.name for region in scout.region_choices.all()],
            })
        return JSONResponse(return_scouts)
    
    ## use the resource instance id to find the graphid
    resource = Resource.objects.get(resourceinstanceid=resourceid)
    graphid = resource.graph_id
    
    ## use the graphid to figure out which HMS-Region node is the one in
    ## this particular resource model
    region_node = Node.objects.get(name="HMS-Region",graph_id=graphid)
    
    ## get the tiles for this resource instance and specifically those
    ## saved for the HMS-Region node
    tiles = Tile.objects.filter(resourceinstance=resourceid,nodegroup_id=region_node.nodegroup_id)
    
    ## iterate through all of the tiles (though in this case there should
    ## only be one) and make a list of the individual values stored for the 
    ## region node
    region_val_uuids = []
    for t in tiles:
        for tt in t.data[str(region_node.nodeid)]:
            region_val_uuids.append(tt)
            
    ## iterate through the values retrieved (which are UUIDs for Value
    ## instances of preflabels) and turn the values which are the actual
    ## labels of the HMS-Region node into Region objects and make a list
    regions = []
    for t in region_val_uuids:
        v = Value.objects.get(valueid=t)
        regions.append(Region.objects.get(name=v.value))

    ## as the scout list gets big this may need some optimizing!
    for scout in all_scouts:
        for region in regions:
            if region in scout.region_choices.all():
                display_name = scout.user.username + " | " + ", ".join(scout.site_interest_type)
                obj = {
                    'id': scout.user_id,
                    'username': scout.user.username,
                    'display_name': display_name,
                    'site_interest_type': scout.site_interest_type,
                    'region_choices': [region.name for region in scout.region_choices.all()],
                }
                if not obj in return_scouts:
                    return_scouts.append(obj)
                    
    return JSONResponse(return_scouts)

def scout_profile(request, username):
    return JSONResponse(ScoutProfile.objects.filter(user__username=username))