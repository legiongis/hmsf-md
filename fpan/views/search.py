import logging
from arches.app.views.search import SearchView


logger = logging.getLogger(__name__)

class FPANSearchView(SearchView):

    def get(self, request):
        return super(FPANSearchView, self).get(request)
