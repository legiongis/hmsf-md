from arches.app.search.elasticsearch_dsl_builder import Dsl

## this could very easily and safely be added to the analogous file in core Arches.

class Type(Dsl):
    """
    https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-type-query.html

    """

    def __init__(self, **kwargs):
        self.type = kwargs.pop('type','')

        self.dsl = {
            'type' : {
                'value' : self.type
            }
        }