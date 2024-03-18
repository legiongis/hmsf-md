# Custom Datatypes & Widgets

**PAGE NEEDS UPDATES!**

## Using the Django ORM in Arches

We have created two Datatype extensions, both of which are meant to allow direct references to objects in the Django ORM. They both inherit from the `DomainListDataType`.

**Username Datatype**

The `Username` Datatype inherits the core Arches `DomainListDataType` and augments that datatype by auto-populating a list of all registered users in the database. The username for a user is shown, while the `pk` for that user is actually stored in the tiles.

Its default widget is the `username-widget`, but it can also be implemented through the `scout-dropdown-widget`.

**Management Area Datatype**

The similar to the Username Datatype, this one also inherits the core Arches `DomainListDataType`. It augments the dropdown list with all Management Area objects in the ORM. This is a model in the hms app.

It can be used with a few different custom widgets (all of which are quite similar).

> **NOTE:**  Currently, this datatype is also used for Management Agency objects in the hms app. This isn't ideal, and could use another look.

All of our widgets simply provide a list of values from the Django ORM, and they are all paired with one of the two datatypes described above.

Five of them inherit the `DomainWidgetViewModel` and are populated in the `js` component directly via context_processor variables:

 - `county-widget` -> `widgetData.dropdownLists.counties`
 - `fpan-region-widget` -> `widgetData.dropdownLists.counties`
 - `management-agency-widget` -> `widgetData.dropdownLists.fpanRegions`
 - `management-area-widget` -> `widgetData.dropdownLists.generalAreas`
 - `username-widget` -> `widgetData.dropdownLists.usernames`

For reference, the context_processor looks something like this:

```
def widget_data(request):

    # only collect this information for a few specific views
    widget_views = ["resource", "graph_designer", "report", "add-resource"]

    data = { 'lists': {} }
    if any([True for i in widget_views if i in request.path.split("/")]):

        all_areas = ManagementArea.objects.all()
        general_areas = all_areas.exclude(category__name="FPAN Region").exclude(category__name="County")
        general_areas = [{
            "id": str(i[0]),
            "selected": "false",
            "text": i[1]
        } for i in general_areas.order_by("display_name").values_list("pk", "display_name") ]

        fpan_regions = [{
            "id": str(i[0]),
            "selected": "false",
            "text": i[1]
        } for i in all_areas.filter(category__name="FPAN Region").values_list("pk", "name") ]

        counties = [{
            "id": str(i[0]),
            "selected": "false",
            "text": i[1]
        } for i in all_areas.filter(category__name="County").values_list("pk", "name") ]

        agencies = [{
            "id": str(i[0]),
            "selected": "false",
            "text": i[1]
        } for i in ManagementAgency.objects.all().values_list("pk", "name") ]

        usernames = [{
            "id": str(i[0]),
            "selected": "false",
            "text": i[1]
        } for i in User.objects.all().order_by("username").values_list("pk", "username")]

        data["lists"]["usernames"] = usernames
        data["lists"]["generalAreas"] = general_areas
        data["lists"]["fpanRegions"] = fpan_regions
        data["lists"]["managementAgencies"] = agencies
        data["lists"]["counties"] = counties

    return data
```

On the other hand, the `scout-widget` does not inherit the `DomainWidgetViewModel`, and it is populated via an AJAX call to a view, `hms.views.scouts_dropdown()`. This is a bit more robust of an implementation, it was our first custom widget and requires more logic than the others. Aligning all patterns across these widgets would be wise.

> Extending the `DomainWidgetViewModel` seemed wise at first, but it comes with some strangeness, like the configuration needing to be saved if you go to this node in the Resource Model graph. It would probably be better to look back at the `scout-widget` implementation.
