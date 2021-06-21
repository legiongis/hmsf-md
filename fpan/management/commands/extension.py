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
import imp
import uuid
import json
from arches.app.models import models
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import IntegrityError


class Command(BaseCommand):
    """
    Commands for managing Arches functions

    """

    def add_arguments(self, parser):

        parser.add_argument(
            "operation",
            choices=["register", "unregister", "list", "update"]
        )

        parser.add_argument(
            "extension_type",
            choices=["widget", "datatype"]
        )

        parser.add_argument("-s", "--source", action="store", dest="source", default="", help="Widget json file to be loaded")

        parser.add_argument("-n", "--name", action="store", dest="name", default="", help="The name of the widget to unregister")

    def handle(self, *args, **options):


        if options["operation"] == "register":
            self.register(options["extension_type"], options["source"])

        if options["operation"] == "unregister":
            self.unregister(options["extension_type"], name=options["name"])

        if options["operation"] == "list":
            self.list(options["extension_type"])

        if options["operation"] == "update":
            self.update(options["extension_type"], options["source"])

    def get_source_details(self, source_path):

        ## load details from a python module (functions, datatypes)
        if source_path.endswith(".py"):

            import imp
            try:
                source = imp.load_source("", source_path)
            ## more precise exception handling would be good here
            except Exception as e:
                raise(e)
            details = source.details
            return details

        ## load details form a json file (widgets, card_components, etc.)
        elif source_path.endswith(".json"):

            with open(source_path) as f:
                details = json.load(f)
            return details

        else:
            print("invalid source path")
            exit()


    def get_orm_entity(self, extension_type):

        if extension_type == "widget":
            return models.Widget
        elif extension_type == "datatype":
            return models.DDataType

    def register(self, extension_type, source):
        """
        Registers a new extension in the database based on the provided source

        """

        details = self.get_source_details(source)

        if extension_type == "widget":

            try:
                uuid.UUID(details["widgetid"])
            except:
                details["widgetid"] = str(uuid.uuid4())
                print("Registering widget with widgetid: {}".format(details["widgetid"]))

            instance = models.Widget(
                widgetid=details["widgetid"],
                name=details["name"],
                datatype=details["datatype"],
                helptext=details["helptext"],
                defaultconfig=details["defaultconfig"],
                component=details["component"],
            )

            instance.save()

        elif extension_type == "datatype":

            dt = models.DDataType(
                datatype=details["datatype"],
                iconclass=details["iconclass"],
                modulename=os.path.basename(source),
                classname=details["classname"],
                defaultwidget=details["defaultwidget"],
                defaultconfig=details["defaultconfig"],
                configcomponent=details["configcomponent"],
                configname=details["configname"],
                isgeometric=details["isgeometric"],
                issearchable=details.get("issearchable", False),
            )

            if len(models.DDataType.objects.filter(datatype=dt.datatype)) == 0:
                dt.save()
            else:
                print("{0} already exists".format(dt.datatype))

    def update(self, extension_type, source):
        """
        Updates an existing widget in the arches db

        """
        details = self.get_source_details(source)
        entity = self.get_orm_entity(extension_type)

        if extension_type == "widget":
            instance = entity.objects.get(name=details["name"])
            instance.datatype = details["datatype"]
            instance.helptext = details["helptext"]
            instance.defaultconfig = details["defaultconfig"]
            instance.component = details["component"]
            instance.save()

    def unregister(self, extension_type, name):
        """
        Removes an extension of the specified type from the database

        """
        entity = self.get_orm_entity(extension_type)
        try:
            if extension_type == "datatype":
                instance = entity.objects.get(datatype=name)
            else:
                instance = entity.objects.get(name=name)
            instance.delete()
        except Exception as e:
            print(e)

    def list(self, extension_type):
        """
        Lists registered extensions of a specified type

        """

        entity = self.get_orm_entity(extension_type)
        try:
            instances = entity.objects.all()
            for instance in instances:
                if extension_type == "datatype":
                    print(instance.datatype)
                else:
                    print(instance.name)
        except Exception as e:
            print(e)
