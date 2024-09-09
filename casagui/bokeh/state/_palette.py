########################################################################
#
# Copyright (C) 2022
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
#        Internet email: casa-feedback@nrao.edu.
#        Postal address: AIPS++ Project Office
#                        National Radio Astronomy Observatory
#                        520 Edgemont Road
#                        Charlottesville, VA 22903-2475 USA
#
########################################################################
'''Functions for palette access.'''
import re
from bokeh import palettes as __palettes
from ...utils import static_vars

__palette_list = sorted( [ p for p in dir(__palettes) if isinstance(getattr(__palettes,p), tuple) if len(getattr( __palettes, p )) == 256 ] )
__palette_names = [ re.sub(r'\d+$', '', p) for p in __palette_list ]

__palette_map = dict( zip( __palette_names, __palette_list ) )

def available_palettes ( ):
    '''returns list of palette pretty names'''
    return __palette_names

def find_palette( name ):
    '''fetches palette by the pretty name'''
    if name not in __palette_map:
        return None
    return getattr( __palettes, __palette_map[name] )

@static_vars( raw=None, pretty=None )
def default_palette( raw=False ):
    '''returns the full name (raw or pretty version)'''
    if default_palette.pretty is None:
        if 'Plasma' in __palette_map:
            default_palette.pretty = 'Plasma'
            default_palette.raw = __palette_map['Plasma']
        else:
            default_palette.pretty = __palette_names[0]
            default_palette.raw = __palette_map[__palette_names[0]]
    return default_palette.raw if raw else default_palette.pretty
