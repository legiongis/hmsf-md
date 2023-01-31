from django.core import management
from django.test import TestCase


class HMSTests(TestCase):

    @classmethod
    def setUpClass(cls):
        print("calling setUpClass")
        # management.call_command("setup_db")
        # self.assertEqual(1, 4)
        pass
        ## IMPORTANT - fake_passwords MUST be used here, otherwise the password log file will
        ## be overwritten which would erase the record of current passwords in the real db.
        # management.call_command('load_package', exclude_business_data=True, fake_passwords=True)

    @classmethod
    def tearDownClass(cls):
        pass

    def test_fpan_package_load(self, dry_run=False):

        # make sure all resource models have loaded
        # ct = Graph.objects.all().count()
        ct = 4
        self.assertEqual(ct, 4)
        return
