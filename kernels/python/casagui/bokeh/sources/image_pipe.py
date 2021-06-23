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
    __im_path = None
    __im = None
    __im_shape = None
    __chan_shape = None

    address = Tuple( String, Int, help="two integer sequence representing the address and port to use for the websocket" )

    __implementation__ = TypeScript( "" )

    def shape( self ):
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
        #### index is expected to be [STOKES,CHANNEL]
        if self.__im is None:
            raise RuntimeError('no image is available')
        return np.squeeze( self.__im.getchunk( blc=[0,0] + index,
                                               trc=self.__chan_shape + index) ).transpose( )
    def spectra( self, index ):
        #### index is expected to be [RA, DEC, STOKES]
        if self.__im is None:
            raise RuntimeError('no image is available')
        print("\t>>>>---> fetching %s" % index)
        return np.squeeze( self.__im.getchunk( blc=index + [0],
                                               trc=index + self.__im_shape[-1] ) )

    def __init__( self, image, *args, **kwargs ):
        super( ).__init__( *args, **kwargs )
        self.__open( image )

    async def process_messages( self, websocket, path ):
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
                spectra = self.spectra(cmd['index'])
                msg = { 'id': cmd['id'],
                        'message': transform_column_source_data( { 'd': [ spectra ] } ) }
                await websocket.send(json.dumps(msg))
            else:
                print("received messate in python with unknown 'action' value: %s" % cmd)

