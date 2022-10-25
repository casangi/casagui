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
#        Internet email: aips2-request@nrao.edu.
#        Postal address: AIPS++ Project Office
#                        National Radio Astronomy Observatory
#                        520 Edgemont Road
#                        Charlottesville, VA 22903-2475 USA
#
########################################################################
'''Functions for palette access.'''
from bokeh import palettes as __palettes
from ...utils import static_vars

__palette_list = [ p for p in dir(__palettes) if isinstance(getattr(__palettes,p), tuple) ]

def available_palettes ( ):
    return __palette_list

def find_palette( name ):
    if name not in __palette_list:
        return None
    return getattr( __palettes, name )

@static_vars(result=None)
def default_palette( ):
    if default_palette.result is None:
        result = None         ### look for palette called 'Plasma...' with the most colors
        fallback = None       ### if none is found fall back to the longest palette name
        for p in __palette_list:
            if fallback is None:
                fallback = p
            elif len(p) > len(fallback):
                fallback = p
            elif len(p) == len(fallback) and p > fallback:
                fallback = p
            if result is None:
                if p.startswith('Plasma'):
                    result = p
            elif p.startswith('Plasma'):
                if len(p) > len(result):
                    result = p
                elif len(p) == len(result) and p > result:
                    result = p
            if result is not None:
                default_palette.result = result
            else:
                default_palette.result = fallback
    return default_palette.result
