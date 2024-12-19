import os
import json
from django.conf import settings
from django.core import management
from django.test import TestCase

from hms.models import (
    Scout,
    LandManager,
    ManagementArea,
    ManagementAreaCategory,
)

# from hms.utils import TestUtils
# from hms.helpers import (
#     create_test_scouts,
#     create_test_landmanagers,
# )



class AccountTests(TestCase):

    @classmethod
    def setUpClass(cls):
        
        # management.call_command('packages',
        #     operation='load_package',
        #     source=os.path.join(settings.APP_ROOT, 'pkg'),
        #     yes=True
        # )

        # create_mock_landmanagers()
        # create_hardy_boys_accounts()

        pass
        ## IMPORTANT - fake_passwords MUST be used here, otherwise the password log file will
        ## be overwritten which would erase the record of current passwords in the real db.
        # management.call_command('load_package', exclude_business_data=True, fake_passwords=True)

    @classmethod
    def tearDownClass(cls):
        pass

    def test_001_load_fpan_regions(self, dry_run=False):

        management.call_command("loaddata", "management-area-categories")
        self.assertEqual(ManagementAreaCategory.objects.all().count(), 8)

        management.call_command("loaddata", "management-areas-fpan-region")
        self.assertEqual(ManagementArea.objects.all().count(), 8)

    def test_002_scout_creation(self, dry_run=False):

        management.call_command("loaddata", "management-area-categories")
        management.call_command("loaddata", "management-areas-fpan-region")

        from hms.utils import TestUtils
        TestUtils().create_test_scouts()
        self.assertEqual(Scout.objects.all().count(), 4)

    def test_003_landmanager_creation(self, dry_run=False):

        management.call_command("loaddata", "management-area-categories")
        management.call_command("loaddata", "management-agencies")
        management.call_command("loaddata", "management-areas-aquatic-preserve")
        management.call_command("loaddata", "management-areas-conservation-area")
        management.call_command("loaddata", "management-areas-fwcc")
        management.call_command("loaddata", "management-areas-state-forest")
        management.call_command("loaddata", "management-areas-state-park")

        from hms.utils import TestUtils
        TestUtils().create_test_landmanagers()
        self.assertEqual(LandManager.objects.all().count(), 5)
