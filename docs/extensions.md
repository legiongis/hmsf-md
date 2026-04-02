# Datatypes & Widgets

## `scout-widget`

The `scout-widget` provides a dropdown of Scout users, so that they can be assigned to Archaeological Site resource instances. It uses the `string` datatype from Core Arches.

The download list is populated dynamically by an AJAX call to a custom view (`/scouts/`) that returns a list of scout names and ids.  This view can be optionally provided a resource id (`/scouts/?resourceid=<uuid>`), which will be used to look up the FPAN Region for that resource, and the returned list of Scouts will be filtered to only include Scouts that have indicated they want to monitor sites within that region.

## `username-widget`

The `username-widget` performs a similar function to the `scout-widget`, but with a different strategy. Instead of the `string` datatype, it uses a custom `username-datatype` (see below). It also inherits from the core Arches `domain-widget` which provides a nice interface and the ability to store multiple values.

The entries for all available usernames to pick from is provided via a context processor function, and the template is customized to auto-populate with the current user's username.

> **Note:** Extending the `DomainWidgetViewModel` has its benefits, but also comes with some strangeness, like the configuration needing to be saved if you go to this node in the Resource Model graph. It would probably be better to look back at the `scout-widget` implementation and perhaps combine these approaches.

## `username-datatype`

The `Username` Datatype inherits the core Arches `DomainListDataType` and augments that datatype by auto-populating a list of all registered users in the database. The username for a user is shown, while the `pk` for that user is actually stored in the tiles.

Its default widget is the `username-widget`, but it could also be implemented through the `scout-widget`.
