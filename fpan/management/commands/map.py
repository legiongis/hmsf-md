"""
ARCHES - a program developed to inventory and manage immovable cultural heritage.
Copyright (C) 2013 J. Paul Getty Trust and World Monuments Fund

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import os
import uuid
import json
from arches.app.models.models import MapSource, MapLayer
from django.db import transaction
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import IntegrityError


class Command(BaseCommand):
    """
    Commands for managing Arches functions

    """

    def add_arguments(self, parser):

        parser.add_argument(
            "operation",
            choices=["add-layer", "remove-layer", "list-layers"]
        )

        parser.add_argument(
            "-s", "--source",
            help="Widget json file to be loaded",
        )

        parser.add_argument(
            "-n", "--name",
            help="The name of the Map Layer to remove"
        )

    def handle(self, *args, **options):


        if options["operation"] == "add-layer":
            self.add_layer(
                options["layer_name"], options["mapbox_json_path"], options["layer_icon"], options["is_basemap"],
            )

        if options["operation"] == "remove-layer":
            self.remove_layer(options["name"])

        if options["operation"] == "list-layers":
            self.list()


    def add_layer(self, layer_name=False, mapbox_json_path=False, layer_icon="fa fa-globe", is_basemap=False,
    ):
        """not yet implemented"""
        if layer_name is not False and mapbox_json_path is not False:
            with open(mapbox_json_path) as data_file:
                data = json.load(data_file)
                with transaction.atomic():
                    for layer in data["layers"]:
                        if "source" in layer:
                            layer["source"] = layer["source"] + "-" + layer_name
                    for source_name, source_dict in data["sources"].items():
                        map_source = MapSource.objects.get_or_create(name=source_name + "-" + layer_name, source=source_dict)
                    map_layer = MapLayer(
                        name=layer_name, layerdefinitions=data["layers"], isoverlay=(not is_basemap), icon=layer_icon
                    )
                    try:
                        map_layer.save()
                    except IntegrityError as e:
                        print("Cannot save layer: {0} already exists".format(layer_name))

    def remove_layer(self, layer_name):
        try:
            layer = MapLayer.objects.get(name=layer_name)
        except MapLayer.DoesNotExist:
            print(f'error: Map Layer "{layer_name}" does not exist.')
            return
        sources = set([i.get("source") for i in layer.layerdefinitions])
        with transaction.atomic():
            # list through and delete sources that aren't None
            for source in [i for i in sources if i]:
                print(f'removing Map Source "{source}"')
                try:
                    MapSource.objects.get(name=source).delete()
                except MapSource.DoesNotExist:
                    pass
            print(f'removing Map Layer "{layer_name}"')
            layer.delete()

    def list(self):
        """
        Lists all registered map layers and the sources they use.
        """

        layers = MapLayer.objects.all()
        print(f"-- {layers.count()} Map Layers --")
        
        for layer in layers:
            print(f"{layer.name}")
            sources = set([i.get("source") for i in layer.layerdefinitions])
            print(f"  source(s): {', '.join([i for i in sources if i is not None])}")
