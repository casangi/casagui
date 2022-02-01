########################################################################
#
# Copyright (C) 2021,2022
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
########################################################################
from ...utils import path_to_url, static_vars, have_network
from ...resources import version
from .. import bokeh_version
from os.path import dirname, join, basename


@static_vars(initialized=False,do_local_subst=not have_network( ))
def initialize_bokeh( libs=None, dev=0 ):
    """Initialize `bokeh` for use with the ``casaguijs`` extensions.

    The ``casaguijs`` extensions for Bokeh are built into a stand-alone
    external JavaScript file constructed for the specific version of
    Bokeh that is being used. The URL or the local path to a locally
    built verion must be supplied as the ``libs`` parameter. If ``libs``
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

    if initialize_bokeh.initialized:
        ### only initialize once...
        return

    ###
    ### if no network is available, substitute local JavaScript libraries
    ### for remote URLs
    ###

    library_hashes = {
        ### --------------------------------------------------------------------------------------------------
        ### Generate hashes with:
        ### echo `cat casaguijs-v0.0.2.0-b2.3.js | openssl dgst -sha384 -binary | openssl base64 -A`
        ### ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---
        ### NOTE: with the conversion from Bokeh 2.3.3 to 2.4.1, it seems that the security hashes are no
        ### longer included in the generated HTML.
        ### --------------------------------------------------------------------------------------------------
        'casaguijs-v0.0.2.0-b2.3.js': 'EtB9H3ooIK3inPGx9RsRXeUv/COHtArEjhZUr7P75GBUPl+lAoGH/tqoAc1sV5jD',
        'casaguijs-v0.0.2.0-b2.3.min.js': 'jAFFXRC9B93jSanS1dmqo+l/3rkcBqM48uTMN+SFcY7GPC/IPeEoI+p+Za5ztkcm',
        'casaguijs-v0.0.3.0-b2.4.min.js': '23DOS7ISXIG8BRyIsD7vINUllDbo8NDCozIGBy7jGC+M14Z+axfF7j4bruA2ZnzL',
        'casaguijs-v0.0.3.0-b2.4.js': 'OmIWKy37YXZf973kemdoFd2L/h0I9AY/hsP5PMdk5/g5xlgj16yk6b0cgO01UMxM'
    }
    ### --------------------------------------------------------------------------------------------------
    ### casagui will ship with local versions of the Bokeh and casaguijs libraries which can be used
    ### when there is no network connectivity...
    ### --------------------------------------------------------------------------------------------------
    local_libraries = {
        'bokeh-2.4.1.min.js': join( dirname(__file__), 'js', 'bokeh-2.4.1.min.js' ),
        'bokeh-gl-2.4.1.min.js':  join( dirname(__file__), 'js', 'bokeh-gl-2.4.1.min.js' ),
        'bokeh-widgets-2.4.1.min.js':  join( dirname(__file__), 'js', 'bokeh-widgets-2.4.1.min.js' ),
    }

    casalib = None
    casaguijs_libs = None
    casaguijs_url = None

    if libs is None:
        casalib = "casaguijs-v%s.%d-b%s.min.js" % (version,dev,'.'.join(bokeh_version.split('.')[0:2]))
        if initialize_bokeh.do_local_subst:
            casaguijs_url = path_to_url( join( dirname(__file__), 'js', casalib ) )
        else:
            ### ------------------------------------------------------------------------------------------
            ### should potentially find a better download location...
            ### ------------------------------------------------------------------------------------------
            casaguijs_url = "https://casa.nrao.edu/download/javascript/casaguijs/%s/%s" % (version,casalib)
        casaguijs_libs = [ casaguijs_url ]
    else:
        casaguijs_libs = [ libs ] if type(libs) == str else libs
        casaguijs_libs = list(map( path_to_url, casaguijs_libs ))

    from bokeh import resources
    ###
    ### substitute our function for the Bokeh function that retrieves
    ### the security hashes for the javascript files...
    ###
    resources.JSResources._old_hashes = resources.JSResources.hashes
    def hashes( self ):
        result = self._old_hashes
        if casalib is not None and casalib in library_hashes:
            result[casaguijs_url] = library_hashes[casalib]
        return result

    ###
    ### substitute our function for the Bokeh function that retrieves
    ### the javascript files...
    ###
    resources.JSResources._old_js_files = resources.JSResources.js_files
    def js_files( self ):
        if initialize_bokeh.do_local_subst:
            result = [ ]
            for url in self._old_js_files:
                lib = basename(url)
                if lib in local_libraries:
                    result.append( path_to_url(local_libraries[lib]) )
                else:
                    result.append( url )
        else:
            result = self._old_js_files
        result = result + casaguijs_libs
        return result

    resources.JSResources.hashes = property(hashes)
    resources.JSResources.js_files = property(js_files)
    initialize_bokeh.initialized = True
