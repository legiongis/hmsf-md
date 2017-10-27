import os
from django.contrib.gis.utils import LayerMapping
from models.region import Region

# Auto-generated `LayerMapping` dictionary for Region model
region_mapping = {
    'region' : 'REGION',
    'geom' : 'MULTIPOLYGON',
}

region_shp = os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'fixtures', 'fpan_region.shp'),
)

def run(verbose=True):
    lm = LayerMapping(
        Region, region_shp, region_mapping,
        transform=False, encoding='iso-8859-1',
    )
    lm.save(strict=True, verbose=verbose)
