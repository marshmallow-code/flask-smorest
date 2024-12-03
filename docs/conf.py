# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

import importlib.metadata

project = "flask-smorest"
copyright = "Nobatek/INEF4 and contributors"

version = release = importlib.metadata.version("flask_smorest")


# -- General configuration ---------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_issues",
]

intersphinx_mapping = {
    "marshmallow": ("https://marshmallow.readthedocs.io/en/latest/", None),
    "apispec": ("https://apispec.readthedocs.io/en/latest/", None),
    "webargs": ("https://webargs.readthedocs.io/en/latest/", None),
    "werkzeug": ("https://werkzeug.palletsprojects.com/", None),
    "flask": ("https://flask.palletsprojects.com/", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/latest/", None),
}

issues_github_path = "marshmallow-code/flask-smorest"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path .
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"


# -- Options for HTML output -------------------------------------------------

html_theme = "alabaster"
html_theme_options = {
    "description": "Build a REST API on Flask using Marshmallow",
    "description_font_style": "italic",
    "github_user": "marshmallow-code",
    "github_repo": "flask-smorest",
    "github_banner": True,
    "github_type": "star",
    "opencollective": "marshmallow",
    "code_font_size": "0.8em",
    "extra_nav_links": {
        "flask-smorest@PyPI": "http://pypi.org/pypi/flask-smorest",
        "flask-smorest@GitHub": "http://github.com/marshmallow-code/flask-smorest",
    },
}
html_sidebars = {
    "**": ["about.html", "donate.html", "navigation.html", "searchbox.html"],
}
