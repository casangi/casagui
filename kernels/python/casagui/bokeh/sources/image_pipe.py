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
from bokeh.models.sources import DataSource
from bokeh.util.compiler import TypeScript
from bokeh.util.serialization import transform_column_source_data
from bokeh.core.properties import Tuple, String, Int
from casatools import image as imagetool

import asyncio
import websockets
import json

import numpy as np

class ImagePipe(DataSource):
    """The `ImagePipe` allows for updates to Bokeh plots from a CASA or CNGI
    image. This is done using a `websocket`. A `ImagePipe` is created with
    the path to the image, and then it is used as the input to an
    `ImageDataSource` or a `SpectraDataSource`. This allows a single CASA
    or CNGI imge to be opened once and shared among multiple Bokeh plots,
    for example ploting an image channel and a plot of a spectra from the
    image cube.

    Attributes
    ----------
    address: tuple of string and int
        the string is the IP address for the network that should be used and the
        integer is the port number, see ``casagui.utils.find_ws_address``
    """
    __im_path = None
    __im = None
    __im_shape = None
    __chan_shape = None

    address = Tuple( String, Int, help="two integer sequence representing the address and port to use for the websocket" )

    __implementation__ = TypeScript( "" )

    def shape( self ):
        """Retrieve the shape of the image cube.
        """
        return self.__im_shape

    def __open( self, image ):
        if self.__im is not None:
            self.__im.close( )
        self.__im = imagetool( )
        try:
            self.__im.open(image)
        except:
            self.__im = None
            raise RuntimeError('could not open image: %s' % image)
        self.__im_shape = self.__im.shape( )
        self.__chan_shape = list(self.__im_shape[0:2])

    def channel( self, index ):
        """Retrieve one channel from the image cube. The `index` should be a
        two element list of integers. The first integer is the ''stokes'' axis
        in the image cube. The second integer is the ''channel'' axis in the
        image cube.

        Parameters
        ----------
        index: [ int, int ]
            list containing first the ''stokes'' index and second the ''channel'' index
        """
        if self.__im is None:
            raise RuntimeError('no image is available')
        return np.squeeze( self.__im.getchunk( blc=[0,0] + index,
                                               trc=self.__chan_shape + index) ).transpose( )
    def spectra( self, index ):
        """Retrieve one spectra from the image cube. The `index` should be a
        three element list of integers. The first integer is the ''right
        ascension'' axis, the second integer is the ''declination'' axis,
        and the third integer is the ''stokes'' axis.

        Parameters
        ----------
        index: [ int, int, int ]
            list containing first the ''right ascension'', the ''declination'' and
            the ''stokes'' axis
        """
        if self.__im is None:
            raise RuntimeError('no image is available')
        result = np.squeeze( self.__im.getchunk( blc=index + [0],
                                                 trc=index + [self.__im_shape[-1]] ) )
        ### should return spectral freq etc.
        ### here for X rather than just the index
        return { 'x': range(len(result)), 'y': result }

    def __init__( self, image, *args, **kwargs ):
        super( ).__init__( *args, **kwargs )
        self.__open( image )

    async def process_messages( self, websocket, path ):
        """Process messages related to image display updates.

        Parameters
        ----------
        websocket: websocket object
            Websocket serve function passes in the websocket object to use.
        path:
            Websocket serve provides a second parameter.
        """
        count = 1
        async for message in websocket:
            cmd = json.loads(message)
            if cmd['action'] == 'channel':
                chan = self.channel(cmd['index'])
                msg = { 'id': cmd['id'],
                        'message': transform_column_source_data( { 'd': [ chan ] } ) }
                await websocket.send(json.dumps(msg))
                count += 1
            elif cmd['action'] == 'spectra':
                msg = { 'id': cmd['id'],
                        'message': transform_column_source_data( self.spectra(cmd['index']) ) }
                await websocket.send(json.dumps(msg))
            else:
                print("received messate in python with unknown 'action' value: %s" % cmd)

