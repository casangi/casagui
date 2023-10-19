########################################################################
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
########################################################################
'''Specialization of the Bokeh ``DataSource`` for image cube data.'''

import numpy as np
from bokeh.plotting import ColumnDataSource
from bokeh.util.compiler import TypeScript
from bokeh.core.properties import Instance, Tuple, Int, Nullable
from bokeh.models.callbacks import Callback
from ._image_pipe import ImagePipe
from ..state import casalib_url, casaguijs_url

class ImageDataSource(ColumnDataSource):
    """Implementation of a ``ColumnDataSource`` customized for planes from
    `CASA`/`CNGI` image cubes. This is designed to use an `ImagePipe` to
    update the image channel/plane displayed in a browser, app or notebook
    with `bokeh`.

    Attributes
    ----------
    image_source: ImagePipe
        the conduit for updating the channel/plane from the image cube
    """

    init_script = Nullable(Instance(Callback), help="""
    JavaScript to be run during initialization of an instance of an ImageDataSource object.
    """)

    image_source = Instance(ImagePipe)
    _mask_contour_source = Nullable(Instance(ColumnDataSource), help='''
    data source for updating contour polygons
    ''')
    num_chans = Tuple( Int, Int, help="[ num-stokes-planes, num-channels ]" )
    cur_chan  = Tuple( Int, Int, help="[ num-stokes-planes, num-channels ]" )

    __javascript__ = [ casalib_url( ), casaguijs_url( ) ]

    def __init__( self, *args, **kwargs ):
        super( ).__init__( *args, **kwargs )
        mask0 = self.image_source.mask0( [0,0] )
        self.data = { 'img': [ self.image_source.channel( [0,0], np.uint8 ) ],
                      'msk0': [ mask0 if mask0 is not None else None ] }
        if self.image_source.have_mask( ):
            self.data['msk'] = [ self.image_source.mask( [0,0] ) ]
        self.num_chans = list(self.image_source.shape[-2:])
        self.cur_chan  = [ 0, 0 ]

    def mask_contour_source( self, data ):
        if not self._mask_contour_source:
            self._mask_contour_source = ColumnDataSource( data=data )
        return self._mask_contour_source

    def pixel_value( self, chan, index ):
        return self.image_source.pixel_value( chan, index )

    def stokes_labels( self ):
        return self.image_source.stokes_labels( )
