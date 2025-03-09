import os
import json
from django.conf import settings
from django.core import management

from arches.app.models.graph import Graph

from hms.models import (
    Scout,
    LandManager,
    ManagementArea,
    ManagementAreaCategory,
)

from .base_test import HMSTestCase

class AccountTests(HMSTestCase):

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


class LoadingTests(HMSTestCase):

    @classmethod
    def setUpClass(cls):
        management.call_command("setup_hms", use_existing_db=True)

    def test_fpan_package_load(self, dry_run=False):

        # make sure all resource models have loaded
        ct = Graph.objects.all().count()
        self.assertEqual(ct, 4)
        return


class ETLTests(HMSTestCase):

    @classmethod
    def tearDownClass(cls):
        pass

    def test_fpan_package_load(self, dry_run=False):
        pass
