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
import os
import numpy as np
from bokeh.plotting import ColumnDataSource
from casatools import image as imagetool
from bokeh.util.compiler import TypeScript
from bokeh.util.serialization import transform_column_source_data
from bokeh.core.properties import Tuple, String, Int

import json

class ImageDataSource(ColumnDataSource):
    """Implementation of a ``ColumnDataSource`` customized for `CASA`/`CNGI`
    images. This is designed to use an internal websocket to update the image
    channel/plane displayed in a browser, app or notebook with `bokeh`.

    Attributes
    ----------
    address: tuple of str and int
        address to use for the `websocket`, this will go away and be changed
        to a ``ImagePipe`` object in the future
    """
    __im_path = None
    __im = None
    __im_indexes = None            ### perhaps down the road we will want to display
                                   ### only a subset of the planes of the image
    __chan_shape = None

    __implementation__ = TypeScript("")

    address = Tuple( String, Int, help="two integer sequence representing the address and port to use for the websocket" )

    def shape( self ):
        """return the shape of the image cube; along with the change to ``ImagePipe``
        this will change to include the `stokes` dimension of the image cube instead
        of dropping it as is currently done (i.e. the return value will go from being
        a three element list to a four element list

        Returns
        -------
        list of int
            Return a list of ints representing the shape of the image cube
        """
        return self.__chan_shape + [ len(self.__im_indexes) ]

    def channel( self, index, image=None ):
        """Return the channel that is displayed; along with the change to ``ImagePipe``
        the ``index`` parameter will change to include the `stokes` dimension of the
        image cube and the ``image`` parameter will move to the ``ImagePipe`` object.

        Returns:
        numpy array
            Return the channel indicated by the ``index`` parameter
        """
        if image is not None:
            self.__im = imagetool( )
            try:
                self.__im.open(image)
            except:
                self.__im = None
        if self.__im is None:
            raise RuntimeError('no available image')
        s = self.__im.shape( )
        self.__chan_shape = list(s[0:2])
        if len(s) > 2:
            self.__im_indexes = range(0,s[-1])
        elif len(s) == 2:
            self.__im_indexes = range(0,1)
        return np.squeeze( self.__im.getchunk( blc=[0,0,0,self.__im_indexes[index]],
                                               trc=self.__chan_shape + [0,self.__im_indexes[index]]) ).transpose( )

    def __init__( self, image, *args, **kwargs ):
        super( ).__init__( self, data={ 'd': [ self.channel( 87, image ) ] }, *args, **kwargs )

    async def process_messages( self, websocket, path ):
        """Process messages arriving over the web socket; along with the change to ``ImagePipe``
        this loop will move to the ``ImagePipe`` object. More changes may be require to mix
        this into other event loops depending on the constraints of the environment, e.g.
        `notebook`.
        """
        count = 1
        async for message in websocket:
            cmd = json.loads(message)
            chan = self.channel(cmd['value'])
            msg = transform_column_source_data( { 'd': [ chan ] } )
            await websocket.send(json.dumps(msg))
            count += 1

