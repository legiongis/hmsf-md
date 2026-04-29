from typing import Union

from arches.app.models.models import Node
from arches.app.models.resource import Resource
from arches.app.models.tile import Tile


class FMSFResource:
    """A wrapper class around an Arches resource that helps manage FMSF content"""

    instance: Resource
    siteid: Union[str, None]

    def __init__(self, resourceid: str):

        self.instance = Resource.objects.get(pk=resourceid)
        self.siteid = self._get_siteid()

    def _get_siteid(self) -> Union[str, None]:

        node = Node.objects.get(name="FMSF ID", graph=self.instance.graph)
        tiles = Tile.objects.filter(
            resourceinstance_id=self.instance.pk, nodegroup=node.nodegroup
        )
        siteid = None
        for t in tiles:
            if t.data and str(node.pk) in t.data:
                siteid = t.data[str(node.pk)]["en"]["value"]
        return siteid
