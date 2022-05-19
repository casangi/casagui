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
'''Implementation of ``ImagePipe`` class which provides a ``websockets``
implementation for CASA images which allows for interacitve display
of image cube channels in response to user input.'''

import json
import asyncio

from bokeh.models.sources import DataSource
from bokeh.util.compiler import TypeScript
from bokeh.core.properties import Tuple, String, Int, Instance, Nullable
from bokeh.models.callbacks import Callback

import numpy as np
from casatools import regionmanager
from casatools import image as imagetool
from ..utils import pack_arrays
from ...utils import partition, resource_manager

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
    init_script: JavaScript
        this javascript is run when this DataPipe object is initialized. init_script
        is used to run caller JavaScript which needs to be run at initialization time.
        This is optional and does not need to be set.
    """
    __im_path = None
    __im = None
    __chan_shape = None

    init_script = Nullable(Instance(Callback), help="""
    JavaScript to be run during initialization of an instance of an DataPipe object.
    """)

    address = Tuple( String, Int, help="two integer sequence representing the address and port to use for the websocket" )
    shape = Tuple( Int, Int, Int, Int, help="shape: [ RA, DEC, Stokes, Spectral ]" )

    __implementation__ = TypeScript( "" )

    def __open( self, image ):
        if self.__im is not None:
            self.__im.close( )
        self.__im = imagetool( )
        self.__rg = regionmanager( )
        try:
            self.__im.open(image)
            self.__path = image
        except Exception as ex:
            self.__im = None
            raise RuntimeError(f'could not open image: {image}') from ex
        self.__chan_shape = list(self.__im.shape( )[0:2])

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
        index = list(map( lambda i: 0 if i is None else i, index ))
        if index[0] >= self.shape[0]:
            index[0] = self.shape[0] - 1
        if index[1] >= self.shape[1]:
            index[1] = self.shape[1] - 1
        if self.__im is None:
            raise RuntimeError('no image is available')
        result = np.squeeze( self.__im.getchunk( blc=index + [0],
                                                 trc=index + [self.shape[-1]] ) )
        ### should return spectral freq etc.
        ### here for X rather than just the index
        try:
            return { 'x': range(len(result)), 'y': list(result) }
        except Exception:
            ## In this case, result is not iterable (e.g.) only one channel in the cube.
            ## A zero length numpy ndarray has no shape and looks like a float but it is
            ## an ndarray.
            return { 'x': [0], 'y': [float(result)] }

    def __init__( self, image, *args, abort=None, stats=False, **kwargs ):
        super( ).__init__( *args, **kwargs, )
        resource_manager.reg_at_exit(self, '__del__')
        self._stats = stats
        self.__open( image )
        self.shape = list(self.__im.shape( ))
        self.__session = None
        self.__abort = abort

        if self.__abort is not None and not callable(self.__abort):
            raise RuntimeError('abort function must be callable')

    def __del__(self):
        if self.__rg:
            self.__rg.done( )
        if self.__im != None:
            self.__im.done()
            self.__im.close()
            self.__im = None

    def coorddesc( self ):
        ia = imagetool( )
        ia.open(self.__path)
        csys = ia.coordsys( )
        ia.close( )
        return { 'csys': csys, 'shape': tuple(self.shape) }

    def statistics( self, index ):
        """Retrieve statistics for one channel from the image cube. The `index`
        should be a two element list of integers. The first integer is the
        ''stokes'' axis in the image cube. The second integer is the ''channel''
        axis in the image cube.

        Parameters
        ----------
        index: [ int, int ]
            list containing first the ''stokes'' index and second the ''channel'' index
        """
        def singleton( potential_nonlist ):
            # convert a list of a single element to the element
            return potential_nonlist if len(potential_nonlist) != 1 else potential_nonlist[0]
        def sort_result( unsorted_dictionary ):
            part = partition( lambda s: (s.startswith('trc') or s.startswith('blc')), sorted(unsorted_dictionary.keys( )) )
            return { k: unsorted_dictionary[k] for k in part[1] + part[0] }

        reg = self.__rg.box( [0,0] + index, self.__chan_shape + index )
        ###
        ### This seems like it should work:
        ###
        #      rawstats = self.__im.statistics( region=reg )
        ###
        ### but it does not so we have to create a one-use image tool (see CAS-13625)
        ###
        ia = imagetool( )
        ia.open(self.__path)
        rawstats = ia.statistics( region=reg )
        ia.close( )
        return sort_result( { k: singleton([ x.item( ) for x in v ]) if isinstance(v,np.ndarray) else v for k,v in rawstats.items( ) } )

    async def process_messages( self, websocket ):
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
            if 'session' not in cmd:
                await websocket.close( )
                err = RuntimeError(f'session not in: {cmd}')
                if self.__abort is not None:
                    self.__abort( asyncio.get_running_loop( ), err )
                else:
                    raise err
                return
            elif self.__session != None and self.__session != cmd['session']:
                await websocket.close( )
                err = RuntimeError(f"session corruption: {cmd['session']} does not equal {self.__session}")
                if self.__abort is not None:
                    self.__abort( asyncio.get_running_loop( ), err )
                else:
                    raise err
                return

            if cmd['action'] == 'channel':
                chan = self.channel(cmd['index'])
                if self._stats:
                    #statistics for the displayed plane of the image cubea
                    statistics = self.statistics( cmd['index'] )
                    msg = { 'id': cmd['id'],
                            # 'stats': pack_arrays(self.__im.statistics( axes=cmd['index'] )),
                            'message': { 'chan': { 'd': [ pack_arrays(chan) ] },
                                         'stats': { 'labels': list(statistics.keys( )), 'values': pack_arrays(list(statistics.values( ))) } } }
                else:
                    msg = { 'id': cmd['id'],
                            'message': { 'chan': { 'd': [ pack_arrays(chan) ] } } }

                await websocket.send(json.dumps(msg))
                count += 1
            elif cmd['action'] == 'spectra':
                msg = { 'id': cmd['id'],
                        'message': { 'spectrum': pack_arrays( self.spectra(cmd['index']) ) } }
                await websocket.send(json.dumps(msg))
            elif cmd['action'] == 'initialize':
                ###
                ### initialize session identifier
                ###
                if self.__session == None:
                    self.__session = cmd['session']
            else:
                print(f"received messate in python with unknown 'action' value: {cmd}")
