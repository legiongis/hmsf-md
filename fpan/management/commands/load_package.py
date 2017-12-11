from django.core import management
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User, Group
from django.conf import settings
from guardian.shortcuts import assign_perm, get_perms
from arches.app.models.models import Node,NodeGroup,Resource2ResourceConstraint
from arches.app.models.graph import Graph
from arches.app.models.card import Card
from fpan.utils.accounts import load_fpan_state_auth
from fpan.models import Region
from hms.models import Scout
import psycopg2 as db
import os
import glob
import shutil
import json
import uuid


class Command(BaseCommand):

    help = 'drops and recreates the app database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-y',
            '--yes',
            action='store_true',
            dest='yes',
            default=False,
            help='forces the continuation of any command that has a confirmation prompt',
        )
        parser.add_argument(
            '-db',
            '--setup_db',
            action='store_true',
            dest='setup_db',
            default=False,
            help='runs the setup_db command before beginning the load process. wipes everything.',
        )
        parser.add_argument("-c", "--components",
            nargs="*",
            help="email addresses to which the server setup notification will be set (defaults are added below)")
        pass

    def handle(self, *args, **options):

        force = options['yes']
        comp = options['components']
        if not comp:
            comp = 'all'
        self.load_package(source=settings.PACKAGE_PATH,setup_db=options['setup_db'], components=comp)

    def load_package(self, source, setup_db=True, overwrite_concepts='ignore', stage_concepts='keep', components=None):

        ## not in use, as this is now handled at the end of the new 
        ## manage.py setup_db command, which can be added to load_package
        ## with the -db flag
        def load_system_settings():
            update_system_settings = True
            settings_file = settings.SYSTEM_SETTINGS_LOCAL_PATH
            if os.path.exists(settings_file):
                update_system_settings = True
                management.call_command('packages',operation='import_business_data', source=settings_file, overwrite='overwrite')
                
        def load_auth_system(package_dir):
            auth_config_file = os.path.join(package_dir,'auth_config.json')
            if not os.path.isfile(auth_config_file):
                print "no auth_config.json file in package"
                return
                
            with open(auth_config_file,'rb') as configs:
                auth_configs = json.load(configs)
                
            print "\nREMOVING UNECESSARY GROUPS\n-----------------------"
            keep_groups = ["Graph Editor","Resource Editor","RDM Administrator","Guest","Crowdsource Editor"]
            all_groups = Group.objects.exclude(name__in=keep_groups)
            for g in all_groups:
                print "  removing group: "+g.name
                g.delete()
            print "    done"
            
            print "\nclearing all existing users\n----------------------"
            keep_users = ["admin","anonymous"]
            all_users = User.objects.exclude(username__in=keep_users)
            for u in all_users:
                print "  removing user: "+u.username
                u.delete()
            print "    done"
            
            print "\ncreating new Scouts for HMS\n----------------------"
            for group,users in auth_configs.iteritems():
                newgroup = Group.objects.get_or_create(name=group)[0]
                for user,info in users.iteritems():
                    print "  creating user:",user
                    if group == "Scout":
                        newuser = Scout.objects.create_user(user,"",info['password'])
                        newuser.first_name = info['first_name']
                        newuser.last_name = info['last_name']
                        newuser.middle_initial = info['middle_initial']
                        newuser.scoutprofile.site_interest_type = info['site_interests']
                        for region in info['regions']:
                            print region
                            obj = Region.objects.get(name=region)
                            newuser.scoutprofile.region_choices.add(obj)
                        cs_grp = Group.objects.get_or_create(name="Crowdsource Editor")[0]
                        newuser.groups.add(cs_grp)
                    else:
                        newuser = User.objects.create_user(user,"",info['password'])
                        newuser.first_name = info['first_name']
                        newuser.last_name = info['last_name']
                    newuser.save()

        def load_resource_to_resource_constraints(package_dir):
            config_paths = glob.glob(os.path.join(package_dir, 'package_config.json'))
            if len(config_paths) > 0:
                configs = json.load(open(config_paths[0]))
                for relationship in configs['permitted_resource_relationships']:
                    obj, created = Resource2ResourceConstraint.objects.update_or_create(
                        resourceclassfrom_id=uuid.UUID(relationship['resourceclassfrom_id']),
                        resourceclassto_id=uuid.UUID(relationship['resourceclassto_id']),
                        resource2resourceid=uuid.UUID(relationship['resource2resourceid'])
                    )

        def load_resource_views(package_dir):
            resource_views = glob.glob(os.path.join(package_dir, '*', 'business_data','resource_views', '*.sql'))
            try:
                with connection.cursor() as cursor:
                    for view in resource_views:
                        with open(view, 'r') as f:
                            sql = f.read()
                            cursor.execute(sql)
            except Exception as e:
                print e
                print 'Could not connect to db'

        def load_graphs(package_dir):
            branches = os.path.join(package_dir, 'graphs', 'branches')
            resource_models = os.path.join(package_dir, 'graphs', 'resource_models')
            management.call_command('packages',operation='import_graphs', source=branches, overwrite=True)
            management.call_command('packages',operation='import_graphs', source=resource_models, overwrite=True)

        def load_concepts(package_dir):
            concept_data = glob.glob(os.path.join(package_dir, 'reference_data', 'concepts', '*.xml'))
            collection_data = glob.glob(os.path.join(package_dir, 'reference_data', 'collections', '*.xml'))

            for path in concept_data:
                management.call_command('packages',operation='import_reference_data', source=path, overwrite='overwrite', stage='keep')

            for path in collection_data:
                management.call_command('packages',operation='import_reference_data', source=path, overwrite='overwrite', stage='keep')

        def load_mapbox_styles(style_paths, basemap):
            for path in style_paths:
                style = json.load(open(path))
                meta = {
                    "icon": "fa fa-globe",
                    "name": style["name"]
                }
                if os.path.exists(os.path.join(os.path.dirname(path), 'meta.json')):
                    meta = json.load(open(os.path.join(os.path.dirname(path), 'meta.json')))

                self.add_mapbox_layer(meta["name"], path, meta["icon"], basemap)

        def load_tile_server_layers(xml_paths, basemap):
            for path in xml_paths:
                meta = {
                    "icon": "fa fa-globe",
                    "name": os.path.basename(path)
                }
                if os.path.exists(os.path.join(os.path.dirname(path), 'meta.json')):
                    meta = json.load(open(os.path.join(os.path.dirname(path), 'meta.json')))

                self.add_tileserver_layer(meta['name'], path, meta['icon'], basemap)

        def load_map_layers(package_dir):
            basemap_styles = glob.glob(os.path.join(package_dir, '*', 'map_layers', 'mapbox_spec_json', 'basemaps', '*', '*.json'))
            overlay_styles = glob.glob(os.path.join(package_dir, '*', 'map_layers', 'mapbox_spec_json', 'overlays', '*', '*.json'))
            load_mapbox_styles(basemap_styles, True)
            load_mapbox_styles(overlay_styles, False)

            tile_server_basemaps = glob.glob(os.path.join(package_dir, '*', 'map_layers', 'tile_server', 'basemaps', '*', '*.xml'))
            tile_server_overlays = glob.glob(os.path.join(package_dir, '*', 'map_layers', 'tile_server', 'overlays', '*', '*.xml'))
            load_tile_server_layers(tile_server_basemaps, True)
            load_tile_server_layers(tile_server_overlays, False)

        def load_business_data(package_dir):
            business_data = []
            business_data += glob.glob(os.path.join(package_dir, 'business_data','*.json'))
            business_data += glob.glob(os.path.join(package_dir, 'business_data','*.csv'))
            relations = glob.glob(os.path.join(package_dir, 'business_data', 'relations', '*.relations'))

            for path in business_data:
                if path.endswith('csv'):
                    config_file = path.replace('.csv', '.mapping')
                    management.call_command('packages',operation='import_business_data', source=path, overwrite='append')
                else:
                    management.call_command('packages',operation='import_business_data', source=path, overwrite='append')

            for relation in relations:
                management.call_command('packages',operation='import_business_data_relations', source=relation)

            uploaded_files = glob.glob(os.path.join(package_dir, 'business_data','files','*'))
            dest_files_dir = os.path.join(settings.MEDIA_ROOT, 'uploadedfiles')
            if os.path.exists(dest_files_dir) == False:
                os.makedirs(dest_files_dir)
            for f in uploaded_files:
                shutil.copy(f, dest_files_dir)

        def load_extensions(package_dir, ext_type, cmd):
            extensions = glob.glob(os.path.join(package_dir, 'extensions', ext_type, '*'))
            root = settings.APP_ROOT if settings.APP_ROOT != None else os.path.join(settings.ROOT_DIR, 'app')
            component_dir = os.path.join(root, 'media', 'js', 'views', 'components', ext_type)
            module_dir = os.path.join(root, ext_type)
            template_dir = os.path.join(root, 'templates', 'views', 'components', ext_type)

            for extension in extensions:
                templates = glob.glob(os.path.join(extension, '*.htm'))
                components = glob.glob(os.path.join(extension, '*.js'))
                if len(templates) == 1 and len(components) == 1:
                    if os.path.exists(template_dir) == False:
                        os.mkdir(template_dir)
                    if os.path.exists(component_dir) == False:
                        os.mkdir(component_dir)
                    shutil.copy(templates[0], template_dir)
                    shutil.copy(components[0], component_dir)

                modules = glob.glob(os.path.join(extension, '*.json'))
                modules.extend(glob.glob(os.path.join(extension, '*.py')))

                if len(modules) > 0:
                    module = modules[0]
                    shutil.copy(module, module_dir)
                    management.call_command(cmd, 'register', source=module)

        def load_widgets(package_dir):
            load_extensions(package_dir,'widgets', 'widget')

        def load_functions(package_dir):
            load_extensions(package_dir,'functions', 'fn')

        def load_datatypes(package_dir):
            load_extensions(package_dir,'datatypes', 'datatype')
            
        def get_cards(names,graph_instance):
            
            if names == "all":
                cards = Card.objects.filter(graph=graph_instance)
                return (cards,["all"])
            msg = []
            cards = []
            for name in names:
                try:
                    card = Card.objects.get(name=name,graph=graph_instance)
                    cards.append(card)
                    msg.append(name)
                except ObjectDoesNotExist:
                    msg.append(name+" (invalid name)")
            return (cards,msg)
            
        def load_permissions(package_dir):
            """custom load function to add permissions as defined in a package-specific
            manner"""
            
            perm_config_file = os.path.join(package_dir,'permissions_config.json')
            if not os.path.isfile(perm_config_file):
                print "no permissions_config.json file in package"
                return
                
            with open(perm_config_file,'rb') as configs:
                perm_configs = json.load(configs)
                
            valid_perms = [
                'delete_nodegroup',
                'no_access_to_nodegroup',
                'read_nodegroup',
                'write_nodegroup'
            ]
            perm_error = False
            
            for g_name,data in perm_configs.iteritems():
                try:
                    g = Graph.objects.get(name=g_name)
                    if not g.isresource:
                        print "graph: {} - Error: this is a Branch, not a Resource Model\n--".format(g_name)
                        continue
                    print "graph:",g_name
                except ObjectDoesNotExist:
                    print "graph: {} - Error: does not exist\n--".format(g_name)
                    continue
                for group_name, perms in data.iteritems():
                    try:
                        group = Group.objects.get(name=group_name)
                        print "  group:",group_name
                    except ObjectDoesNotExist:
                        print "    group: {} - Error: does not exist\n--".format(group_name)
                        continue
                    for perm_type, card_names in perms.iteritems():
                        if not perm_type in valid_perms:
                            print "    permission: {} - Error: invalid permission type".format(perm_type)
                            perm_error = True
                            continue
                        print "    permission:",perm_type
                        cards,msg = get_cards(card_names,g)
                        if len(cards) > 0:
                            print "      cards: "+", ".join(msg)
                        for c in cards:
                            assign_perm(perm_type,group,c._nodegroup_cache)
            
            if perm_error:
                print "valid permission types:",valid_perms
        
        def load_fixtures(package_dir):
            '''currently only configured to look for .json fixtures'''
            fixture_dir = os.path.join(package_dir,'fixtures')
            if not os.path.isdir(fixture_dir):
                print "no fixture directory found"
                return
                
            for f in os.listdir(fixture_dir):
                if not f.endswith(".json"):
                    continue
                f_path = os.path.join(fixture_dir,f)
                management.call_command('loaddata',f_path)

        def handle_source(source):

            if os.path.isdir(source):
                return source
                
            source_dir = os.path.join(os.getcwd(),'temp_' + datetime.now().strftime('%y%m%d_%H%M%S'))
            os.mkdir(source_dir)
            
            if source.endswith(".zip") and os.path.isfile(source):
                unzip_file(source, source_dir)
                return source_dir
            
            try:
                urllib.urlopen(source)
                zip_file = os.path.join(source_dir,"source_data.zip")
                urllib.urlretrieve(source, zip_file)
                unzip_file(zip_file, source_dir)
                return source_dir
            except:
                pass
            
            return False
        
        ## no need to handle the source now (there is no input for this) because
        ## it is acquired from settings.PACKAGE_PATH
        # source_dir = handle_source(source)
        # if not source_dir:
            # raise Exception("this is an invalid package source")

        if setup_db:
            management.call_command('setup_db',yes=True)
            
        package = settings.PACKAGE_PATH
        
        if 'fixtures' in components or components == 'all':
            print "\n~~~~~~~~ LOAD FIXTURES"
            load_fixtures(package)
            print "done"
                  
        if 'auth' in components or components == 'all':
            print "\n~~~~~~~~ CONFIGURE AUTHENTICATION SYSTEM"
            load_auth_system(package)
            load_fpan_state_auth(mock=True)
            print "done"
        
        if 'widgets' in components or components == 'all':
            print "\n~~~~~~~~ LOAD WIDGETS"
            load_widgets(package)
            print "done"
            
        if 'functions' in components or components == 'all':
            print "\n~~~~~~~~ LOAD FUNCTIONS"
            load_functions(package)
            print "done"
        
        ## loading datatypes not tested in fpan - 10/13/17
        # print "\n~~~~~~~~ LOAD DATATYPES"
        # load_datatypes(package)
        
        if 'concepts' in components or components == 'all':
            print "\n~~~~~~~~ LOAD CONCEPTS & COLLECTIONS"
            load_concepts(package)
            
        if 'graphs' in components or components == 'all':
            print "\n~~~~~~~~ LOAD RESOURCE MODELS & BRANCHES"
            load_graphs(package)
            print "\n~~~~~~~~ ...and RESOURCE TO RESOURCE CONSTRAINTS"
            load_resource_to_resource_constraints(package)
            print "done"
            print "\n~~~~~~~~ ...and APPLYING PERMISSIONS"
            load_permissions(package)
        
        ## loading map layers not tested in fpan - 10/13/17
        # print "\n~~~~~~~~ LOAD MAP LAYERS"
        # load_map_layers(package)
        
        if 'data' in components or components == 'all':
            print "\n~~~~~~~~ LOAD RESOURCES & RESOURCE RELATIONS"
            load_business_data(package)
        
        ## loading resource views not tested in fpan - 10/13/17
        # print "\n~~~~~~~~ LOAD RESOURCE VIEWS"
        # load_resource_views(package)