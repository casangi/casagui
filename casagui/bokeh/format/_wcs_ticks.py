########################################################################
#
# Copyright (C) 2023
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
from bokeh.models import TickFormatter
from bokeh.util.compiler import TypeScript
from bokeh.core.properties import Instance, String
from casagui.bokeh.sources import ImageDataSource
from ..state import casalib_url, casaguijs_url

class WcsTicks(TickFormatter):

    ## which axis are we labeling
    axis = String( )

    ## source containing the WCS information
    image_source = Instance(ImageDataSource)

    __javascript__ = [ casalib_url( ), casaguijs_url( ) ]

    def __init__( self, *args, **kwargs ):
        super( ).__init__( *args, **kwargs )
