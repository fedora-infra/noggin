# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys


topdir = os.path.abspath("../")
sys.path.insert(0, topdir)

import noggin  # NOQA


# -- Project information -----------------------------------------------------

project = 'Noggin'
copyright = '2020, Red Hat, Inc'
author = 'Fedora Infrastructure'

# The short X.Y version
version = ".".join(noggin.__version__.split(".")[:2])

# The full version, including alpha/beta/rc tags
release = noggin.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.extlinks',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Explcitely set the master doc
# https://github.com/readthedocs/readthedocs.org/issues/2569
master_doc = 'index'


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'


# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    "github_user": "fedora-infra",
    "github_repo": "noggin",
    "page_width": "1040px",
    "show_related": True,
    "sidebar_collapse": True,
    "caption_font_size": "140%",
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']


# -- Extension configuration -------------------------------------------------

# -- Options for intersphinx extension ---------------------------------------

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

extlinks = {
    "commit": ("https://github.com/fedora-infra/noggin/commit/%s", ""),
    "issue": ("https://github.com/fedora-infra/noggin/issues/%s", "#"),
    "pr": ("https://github.com/fedora-infra/noggin/pull/%s", "PR#"),
}

# -- Misc -----


def run_apidoc(_):
    from sphinx.ext import apidoc

    apidoc.main(
        [
            "-f",
            "-o",
            os.path.join(topdir, "docs", "_source"),
            os.path.join(topdir, "noggin"),
        ]
    )


def setup(app):
    app.connect("builder-inited", run_apidoc)
