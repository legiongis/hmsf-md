import os
import csv
import logging
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from arches.app.models.resource import Resource
from arches.app.models.graph import Graph
from arches.app.search.search_engine_factory import SearchEngineInstance as se

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    help = 'Checks the current ElasticSearch resource index against the ORM '\
    'objects and prints a list of missing resources to the logs directory.'

    def add_arguments(self, parser):

        parser.add_argument("--index",
            action="store_true",
            default=False,
            help="attempt to index resources that aren't in index."
        )

    def handle(self, *args, **options):

        es_contents = self.get_es_contents()

        graphs = Graph.objects.filter(isresource=True).exclude(name="Arches System Settings")

        for graph in graphs:

            print(graph.name)

            missing = []
            uuid_resids = Resource.objects.filter(graph=graph).values_list('resourceinstanceid', flat=True)
            db_resourceids = set([str(i) for i in uuid_resids])

            try:
                es_resourceids = es_contents[str(graph.pk)]
            except KeyError:
                es_resourceids = set()

            print(f"- in db: {len(db_resourceids)}")
            print(f"- in index: {len(es_resourceids)}")
            if db_resourceids != es_resourceids:
                es_diff = list(es_resourceids - db_resourceids)
                if len(es_diff) > 0:
                    print(f"  {len(es_diff)} indexed resources not in db:")
                    [print("    " + i) for i in es_diff[:5]]
                    if len(es_diff) > 5:
                        print("    ...")
                db_diff = list(db_resourceids - es_resourceids)
                if len(db_diff) > 0:
                    print(f"  {len(db_diff)} db resources not in index:")
                    [print("    " + i) for i in db_diff[:5]]
                    if len(db_diff) > 5:
                        print("    ...")
                    if options["index"]:
                        print("    indexing these resources now...")
                        for id in db_diff:
                            r = Resource.objects.get(pk=id)
                            try:
                                r.index()
                            except Exception as e:
                                print(e)
                                break



    def get_es_contents(self):

        summary = dict()
        for resinfo in self.iterate_all_documents(se, 'resources'):
            resid, graphid = resinfo
            if graphid != 'None':
                if graphid in summary:
                    summary[graphid].add(resid)
                else:
                    summary[graphid] = set([resid])
        return summary

    def iterate_all_documents(self, se, index, pagesize=250, scroll_timeout="1m"):
        """
        Helper to iterate ALL values from a single index. Yields all the documents.
        https://techoverflow.net/2019/05/07/elasticsearch-how-to-iterate-scroll-through-all-documents-in-index/
        """
        is_first = True
        while True:
            # Scroll next
            if is_first: # Initialize scroll
                result = se.search(index=index, scroll="1m", body={
                    "size": pagesize
                })
                is_first = False
            else:
                ## note: need to access the ElasticSearch() instance directly
                ## here, (.es), because the Arches se object doesn't inherit .scroll()
                result = se.es.scroll(body={
                    "scroll_id": scroll_id,
                    "scroll": scroll_timeout
                })
            scroll_id = result["_scroll_id"]
            hits = result["hits"]["hits"]
            # Stop after no more docs
            if not hits:
                break
            # Yield each entry
            yield from ((hit['_source']['resourceinstanceid'], hit['_source']['graph_id']) for hit in hits)
