# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'HMS-Florida Monitoring Database'
copyright = '2024, Legion GIS'
author = 'Adam Cox'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['myst_parser']
myst_heading_anchors = 3

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_material'
html_static_path = ['_static']

html_css_files = [
    'css/style.css',
]

html_show_sourcelink = False

html_theme_options = {

    # Set the name of the project to appear in the navigation.
    'nav_title': 'HMSF-MD Documentation',

    # Specify a base_url used to generate sitemap.xml. If not
    # specified, then no sitemap will be built.
    'base_url': 'https://hms.fpan.us',

    # Set the color and the accent color
    'color_primary': 'grey',
    'color_accent': 'blue',

    # Set the repo location to get a badge with stats
    'repo_url': 'https://github.com/legiongis/hmsf-md',
    'repo_name': 'HMSF-MD',

    # Visible levels of the global TOC; -1 means unlimited
    'globaltoc_depth': 2,
    # If False, expand all TOC entries
    'globaltoc_collapse': False,
    # If True, show hidden TOC entries
    'globaltoc_includehidden': False,

    'localtoc_label_text': "On this page...",

    'master_doc': False,
}

html_sidebars = {
    "**": ["logo-text.html", "globaltoc.html", "localtoc.html", "searchbox.html"]
}
