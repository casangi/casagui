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
from bokeh.models import Model
from bokeh.util.compiler import TypeScript
from bokeh.core.properties import Tuple, Int

class DownsampleState(Model):
    """`DownsampleState` provides the state and communications to implement
    down sampling.
    """
    shape = Tuple( Int, Int, help="on disk image channel shape" )
    raw = Tuple( Int, Int, help="disk pixel size of image that yielded sampled size" )
    ###
    ### Once sampled[0] <= viewport[0][1]-viewport[0][0] and
    ###      sampled[1] <= viewport[1][1]-viewport[1][0]
    ### then the non-downsampling Bokeh tools can be used because the
    ### on-disk, pixel representation is small enough to be available
    ### within javascript
    ###                                                                           shape of channel, may be larger----v
    ###                                                                                                              |
    ###                                                                                         |                    |
    ###       browser                                                                           |                    |
    ###                           v----sampled (may be larger than viewport, allowing panning)  |                    |
    ###                           |    this may not be true because it would imply that the     |                    |
    ###         |                 |    sampled image is downsampled further than it needs       |                    |
    ###         |                 |    to be... probably one of these is redundant              |                    |
    ###         ^---viewport      |                                                             |                    |
    ###                           |                                                             |                    |
    ###                                                                                         |                    |
    ###                                                  raw area sampled to produce sampled----^                    |
    ###                                                  may be smaller than shape due                               |
    ###                                                  to zooming                                                  |
    ###
    sampled = Tuple( Int, Int, help="dimension of the pixels available inside javascript" )
    viewport = Tuple( Tuple( Int, Int), Tuple( Int, Int ), help="blc/trc of selected view (xmin, ymin) and (xmax, ymax)" )
    __implementation__ = TypeScript("")

    def __init__( self, image_source, display_dim, *args, **kwargs ):
        super( ).__init__( *args, **kwargs )
        image_source.downsample_state = self
        shape = image_source.image_source.shape[:2]
        self.shape = shape
        self.raw = shape
        self.sampled = display_dim
        self.viewport = [ [0,0], shape ]
