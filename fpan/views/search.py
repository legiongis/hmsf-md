import logging
from django.http import Http404
from arches.app.views.search import SearchView

from fpan.utils.permission_backend import user_is_anonymous

logger = logging.getLogger(__name__)

class FPANSearchView(SearchView):

    def get(self, request):

        if user_is_anonymous(request.user):
            raise Http404("not found")

        return super(FPANSearchView, self).get(request)
