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
# For extensions
from os.path import dirname, abspath, join
import sys

sys.path.insert(0, abspath(join(dirname(__file__),'extensions')))      # For xref
sys.path.insert(0, abspath(join(dirname(__file__),'..','..')))         # For autoapi
print('----------------------------------------------------------------------------------------------------')
print(sys.path)
print('----------------------------------------------------------------------------------------------------')

# -- Project information -----------------------------------------------------

project = 'casagui'
copyright = '2021,2022, Associated Universities, Inc. Washington DC, USA.'
author = 'CASA visualization team'

# The full version, including alpha/beta/rc tags
release = '0.0.1'


# -- General configuration ---------------------------------------------------
#
# Import hypertext links for use in the documentation
#
print('-------------------------------------------------------------------')
print(sys.path)
print('-------------------------------------------------------------------')
from links.link import *
from links import *

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [ 'sphinx.ext.autodoc',
               'sphinx.ext.napoleon',
               'sphinx.ext.todo',
               'autoapi.extension',
               'xref'
             ]

# configure autoapi
autoapi_dirs = ['../casagui' ]
autoapi_add_toctree_entry = False
autoapi_generate_api_docs = True
autoapi_root = '_api/autoapi'
autoapi_options = ['show-module-summary']
autoapi_template_dir = '_templates'
autoapi_keep_files = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

###
### cause documentation for class.__call__ to be generated
###
def member_skip( app, what, name, obj, would_skip, options ):
    if name == '__call__':
        return False
    return would_skip

def setup(app):
    app.add_css_file('customization.css')
    app.connect( 'autodoc-skip-member', member_skip )
