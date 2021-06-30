########################################################################3
#
# Copyright (C) 2021
# Associated Universities, Inc. Washington DC, USA.
#
# This script is free software; you can redistribute it and/or modify it
# under the terms of the GNU Library General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Library General Public
# License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with this library; if not, write to the Free Software Foundation,
# Inc., 675 Massachusetts Ave, Cambridge, MA 02139, USA.
#
# Correspondence concerning AIPS++ should be adressed as follows:
#        Internet email: aips2-request@nrao.edu.
#        Postal address: AIPS++ Project Office
#                        National Radio Astronomy Observatory
#                        520 Edgemont Road
#                        Charlottesville, VA 22903-2475 USA
#
########################################################################3
from bokeh import resources
from ..utils import path_to_url
from ..resources import version
from . import bokeh_version

def initialize_bokeh( libs=None, dev=0 ):
    """Initialize `bokeh` for use with the ``casaguijs`` extensions.

    The ``casaguijs`` extensions for Bokeh are built into a stand-alone
    external JavaScript file constructed for the specific version of
    Bokeh that is being used. The URL or the local path to a locally
    built verion must be supplied as the ``lib`` parameter. If ``lib``
    is ``None`` then the default is to use the published verison of
    ``casaguijs`` extensions built and installed for `HTTP` access.

    Parameters
    ----------
    libs: None or str or list of str
        javascript library to load could be a local path, a URL or None.
        None is the default in which case it loads the published library
        for the current version of ``casaguijs`` and ``bokeh``
    dev: int, optional
        Chrome caches the javascript files. This parameter allows for
        specifying `dev` allows for including a development version
        for incremental updates to JavaScript from website.
    """

    casaguijs_libs = [ "https://casa.nrao.edu/download/javascript/casaguijs/%s/casaguijs-v%s.%d-b%s.min.js" % (version,version,dev,'.'.join(bokeh_version.split('.')[0:2])) ] if libs is None else \
        [ libs ] if type(libs) == str else libs
    casaguijs_libs = list(map( path_to_url, casaguijs_libs ))
    original_func = resources._get_cdn_urls
    def __get_cdn_urls(version=None, minified=True, legacy=False):
        from copy import deepcopy
        result = original_func( version, minified, legacy )
        resources_result = deepcopy(result)
        def get_urls( components, kind ):
            temp_result = resources_result["urls"](components, kind)
            return temp_result + casaguijs_libs if kind == 'js' else temp_result
        result["urls"] = get_urls
        return result
    resources._get_cdn_urls = __get_cdn_urls
