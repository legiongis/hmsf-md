from django.core import management
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from django.conf import settings
import psycopg2 as db
import os, string, random, csv
from arches.db.install import truncate_db
from arches.management.commands.packages import Command as packages

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

    def handle(self, *args, **options):

        force = options['yes']
        self.setup_db(force)
        self.build_fpan_groups()
        
    def setup_db(self,force=False):
        
        print "setting up the database"
        if not force:
            c = raw_input("  -- this will erase the entire database. continue? y/n >> ")
            if not c.lower().startswith("y"):
                print "     command cancelled."
                return
                
        db_settings = settings.DATABASES['default']
        truncate_path = os.path.join(settings.ROOT_DIR, 'db', 'install', 'truncate_db.sql')
        db_settings['truncate_path'] = truncate_path

        truncate_db.create_sqlfile(db_settings, truncate_path)

        os.system('psql -h %(HOST)s -p %(PORT)s -U %(USER)s -d postgres -f "%(truncate_path)s"' % db_settings)

        management.call_command('migrate')

        # self.import_graphs(os.path.join(settings.ROOT_DIR, 'db', 'system_settings', 'Arches_System_Settings_Model.json'), overwrite_graphs=True)
        # self.import_business_data(os.path.join(settings.ROOT_DIR, 'db', 'system_settings', 'Arches_System_Settings.json'), overwrite=True)

        # local_settings_available = os.path.isfile(os.path.join(settings.SYSTEM_SETTINGS_LOCAL_PATH))

        # if local_settings_available == True:
            # self.import_business_data(settings.SYSTEM_SETTINGS_LOCAL_PATH, overwrite=True)
            
        # packages.build_permissions(packages)


        # dbinfo = settings.DATABASES['default']

        # Postgres version
        # conn = db.connect(host=dbinfo['HOST'], user=dbinfo['USER'],
                        # password=dbinfo['PASSWORD'], port=int(dbinfo['PORT']))
        # conn.autocommit = True
        # cursor = conn.cursor()
        # try:
            # cursor.execute("DROP DATABASE " + "yay")
        # except:
            # pass
        # cursor.execute("CREATE DATABASE " + "yay" + " WITH ENCODING 'UTF8'")
        
        # management.call_command('makemigrations')
        # management.call_command('migrate')

        # print("making admin...")
        
        # default_user = User.objects.create_user('admin','','cspmaster')
        # default_user.is_staff = True
        # default_user.is_superuser = True
        # default_user.save()
        
        
        # print("admin superuser created. password = cspmaster.")
        
    def build_fpan_groups(self):
    
        print "\nREMOVING UNECESSARY GROUPS\n-----------------------"
        keep_groups = ["Graph Editor","Resource Editor","RDM Administrator","Guest"]
        all_groups = Group.objects.filter()
        for g in all_groups:
            if not g.name in keep_groups:
                print "  removing group: "+g.name
                g.delete()
        
        print "\nADDING FPAN GROUPS AND TEST USERS\n----------------"
        groups_users = {
            "State Park":["TomokaStatePark","LakeLouisaStatePark"],
            "FL BAR":["fl_bar_user"],
            "FMSF":["fmsf_user"],
            "FWC":["fwc_user"],
            "FL Forestry":["fl_forestry_user"],
            "FL Aquatic Preserve":["fl_aquatic_preserve_user"],
            "Scout":["scout_user"]
        }
        
        print "  creating groups and default users...",
        outlist = []
        for group, userlist in groups_users.iteritems():
            print "  creating group: "+group
            newgroup = Group.objects.get_or_create(name=group)[0]
            
            for user in userlist:
                pw = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
                try:
                    existing_user = User.objects.get(username=user)
                    existing_user.delete()
                except:
                    pass
                print "    -- adding new user: {} ({})".format(user,pw)                    
                newuser = User.objects.create_user(user,"",pw)
                newuser.groups.add(newgroup)
                outlist.append((user,pw))
                
        with open(os.path.join(settings.SECRET_LOG,"initial_user_info.csv"),"wb") as outcsv:
            write = csv.writer(outcsv)
            write.writerow(("username","password"))
            for user_pw in outlist:
                write.writerow(user_pw)