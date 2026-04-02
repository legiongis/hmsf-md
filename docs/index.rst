.. HMSF-MD Docs documentation master file, created by
   sphinx-quickstart on Sat Sep 23 16:18:56 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

HMS-Florida Monitoring Database
===============================

This documentation contains instructions for administrators working with the HMS-Florida Monitoring database, as well as developer documentation to help maintainers understand and manage the code base.

We have extended Arches using built-in `extension patterns <https://arches.readthedocs.io/en/stable/developing/extending/creating-extensions/>`_ to add some custom functionalities, mainly stemming from our need to protect archaeological data from public access. In some cases, we had hand-built some of these customizations, only to later roll them up into Arches patterns as the core code-base took on a more extensibility-focused nature.

For admins
----------

.. toctree::
   :maxdepth: 2

   guides

For developers
--------------

.. toctree::
   :maxdepth: 2

   permissions
   map-layers
   extensions
   search-filter
   etl-modules
