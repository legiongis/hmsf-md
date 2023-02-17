from django.core.management.base import BaseCommand, CommandError
from arches.app.models.models import Value, Concept, Relation, DLanguage, DValueType
from fpan.models import ManagedArea

class Command(BaseCommand):

    help = 'bulk addition of user accounts from a csv file'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):

        self.add_managed_area_concepts()

    def add_managed_area_concepts(self):

        legacyscope = "hms.fpan.us/rdm/"

        # create some necessary objects
        pref = DValueType.objects.get(valuetype="prefLabel")
        lang = DLanguage.objects.get(languageid="en-US")

        # create the new topconcept
        ma_name_tc = Concept()
        ma_name_tc.nodetype_id = "Concept"
        ma_name_tc.legacyoid = legacyscope + str(ma_name_tc.conceptid)
        ma_name_tc.save()

        ma_name_tc_v = Value()
        ma_name_tc_v.value = "Managed Area Name"
        ma_name_tc_v.language = lang
        ma_name_tc_v.valuetype = pref
        ma_name_tc_v.concept = ma_name_tc
        ma_name_tc_v.save()

        # link to the HMS thesaurus
        scheme = Concept.objects.get(conceptid="3d33cfc4-43b3-4bf8-aa37-44baf1e6895e")
        rel = Relation()
        rel.conceptfrom_id = scheme.conceptid
        rel.conceptto_id = ma_name_tc.conceptid
        rel.relationtype_id = "hasTopConcept"
        rel.save()

        # create the new collection
        ma_name_coll = Concept()
        ma_name_coll.nodetype_id = "Collection"
        ma_name_coll.legacyoid = legacyscope + str(ma_name_coll.conceptid)
        ma_name_coll.save()

        ma_name_coll_v = Value()
        ma_name_coll_v.value = "Managed Area Name"
        ma_name_coll_v.language = lang
        ma_name_coll_v.valuetype = pref
        ma_name_coll_v.concept = ma_name_coll
        ma_name_coll_v.save()

        for ma in ManagedArea.objects.all():

            # create and save the new concept
            c = Concept()
            c.nodetype_id = "Concept"
            c.legacyoid = legacyscope + str(c.conceptid)
            c.save()

            # create a relation to set the concept within the top concept
            r1 = Relation()
            r1.conceptfrom_id = ma_name_tc.conceptid
            r1.conceptto_id = c.conceptid
            r1.relationtype_id = "narrower"
            r1.save()

            # create a relation to set the concept in the collection
            r2 = Relation()
            r2.conceptfrom_id = ma_name_coll.conceptid
            r2.conceptto_id = c.conceptid
            r2.relationtype_id = "member"
            r2.save()

            # add the preflabel for the concept based on the name of the managed area
            v = Value()
            v.value = ma.name
            v.language = lang
            v.valuetype = pref
            v.concept = c
            v.save()

            print(f"{ma.name} saved")