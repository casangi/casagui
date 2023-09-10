########################################################################
#
# Copyright (C) 2021,2022,2023
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
'''This contains functions to inject the ``casaguijs`` library into the
generated HTML that is used to display the Bokeh plots that ``casagui``'s
applications produce'''
import os
import re
from os import path
from os.path import dirname, join, basename, abspath
from bokeh import resources
from ...utils import path_to_url, static_vars, have_network


###!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
###!!!!! Later 'do_local_subst' should be used to substitute local cached Bokeh !!!!!
###!!!!! javascript libraries when no network is available.                     !!!!!
###!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
@static_vars( initialized=False,
              do_local_subst=not have_network( ) )
def initialize_bokeh( bokehjs_subst=None ):
    """Initialize `bokeh` for use with the ``casaguijs`` extensions.

    The ``casaguijs`` extensions for Bokeh are built into a stand-alone
    external JavaScript file constructed for the specific version of
    Bokeh that is being used. Previously the CASA minified JavaScript
    libraries were loaded from the network. Now these libraries are
    included in a ``__js__`` directory within the casagui Python package.
    If users need to debug JavaScript problems, non-minified versions
    can be copied into the ``__js__`` directory to replace the existing
    libraries. To debug within the bokehjs library, a URL or a path
    can be supplied by the ``bokehjs_subst`` parameter and it will be
    substituted for the standard Bokeh library.

    Parameters
    ----------
    bokehjs_subst: None or str or list of str
        Bokeh dependent javascript library which is loaded after all
        other Bokeh libraries have been loaded. This path could be a
        local path, a URL or None. None is the default in which case
        it loads the published library for the current version of
        ``casaguijs`` and ``bokeh``

    Example
    -------
    from casagui.bokeh.state import initialize_bokeh
    initialize_bokeh( bokehjs_subst="/tmp/casaguijs.min.js" )
    """

    if initialize_bokeh.initialized:
        ### only initialize once...
        return

    initialize_bokeh.initialized = True
    resources.Resources._old_js_files = resources.Resources.js_files
    def js_files( self ):
        ########################################################################
        ### Function that will replace the member function within Bokeh that ###
        ### returns the URLs for Bokeh initialization...                     ###
        ########################################################################
        def expand_paths( replacement ):
            ### turn all paths into URLs
            ### turn a single string into a list with one string
            if replacement is None:
                return [ ]
            if type(replacement) == str:
                if path.isfile(replacement):
                    return [ f'''file:/{abspath(replacement)}''' ]
                else:
                    return replacement
            if type(replacement) == list:
                result = [ ]
                for u in replacement:
                    if path.isfile(u):
                        result.append( f'''file:/{abspath(u)}''' )
                    else:
                        result.append( u )
                return result
            return [ ]
        def casaguijs_predicate( s ):
            ### detect casaguijs library URL
            return basename(s).startswith('casaguijs')
        def replace_bokehjs( urls, replacement ):
            ### substitute replacement list for the bokehjs library URL
            result = [ ]
            for url in urls:
                if re.match( r'.*/bokeh-\d+\.\d+\.\d+(?:\.min)?\.js$', url ):
                    result += replacement
                else:
                    result.append(url)
            return result

        user_bokehjs_replacement = expand_paths(bokehjs_subst)
        sys_urls = resources.Resources._old_js_files.fget(self)
        if len(user_bokehjs_replacement) == 0:
            ### move casaguijs library after Bokeh libraries
            return [x for x in sys_urls if not casaguijs_predicate(x)] + [x for x in sys_urls if casaguijs_predicate(x)]
        else:
            ### replace bokehjs library with bokehjs_subst and move casaguijs library after Bokeh libraries
            return replace_bokehjs( [x for x in sys_urls if not casaguijs_predicate(x)], user_bokehjs_replacement ) + [x for x in sys_urls if casaguijs_predicate(x)]

    resources.Resources.js_files = property(js_files)
    return
