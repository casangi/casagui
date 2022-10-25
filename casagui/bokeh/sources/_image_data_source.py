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

from bokeh.plotting import ColumnDataSource
from bokeh.util.compiler import TypeScript
from bokeh.core.properties import Instance, Tuple, Int, Nullable
from bokeh.models.callbacks import Callback
from ._image_pipe import ImagePipe

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
    num_chans = Tuple( Int, Int, help="[ num-stokes-planes, num-channels ]" )
    cur_chan  = Tuple( Int, Int, help="[ num-stokes-planes, num-channels ]" )

    __implementation__ = TypeScript("")

    def __init__( self, *args, **kwargs ):
        super( ).__init__( *args, **kwargs )
        self.data = { 'img': [ self.image_source.channel( [0,0] ) ],
                      'msk': [ self.image_source.mask( [0,0] ) ] }
        self.num_chans = list(self.image_source.shape[-2:])
        self.cur_chan  = [ 0, 0 ]
