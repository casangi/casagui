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
import types

from bokeh.models.sources import DataSource
from bokeh.util.compiler import TypeScript
from bokeh.core.properties import Tuple, String, Int, Instance, Nullable
from bokeh.models.callbacks import Callback

import numpy as np
try:
    import casatools as ct
    from casatools import regionmanager
    from casatools import image as imagetool
except:
    ct = None
    from casagui.utils import warn_import
    warn_import('casatools')

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

    def __open_image( self, image ):
        if self.__img is not None:
            self.__img.close( )
        self.__img = imagetool( )
        self.__rgn = regionmanager( )
        try:
            self.__img.open(image)
            self.__image_path = image
        except Exception as ex:
            self.__img = None
            self.__image_path = None
            raise RuntimeError(f'could not open image: {image}') from ex
        imshape = self.__img.shape( )
        if self.__msk is not None and all(self.__msk.shape( ) != imshape):
            raise RuntimeError(f'mismatch between image shape ({imshape}) and mask shape ({self.__msk.shape( )})')
        if self.__chan_shape is None: self.__chan_shape = list(imshape[0:2])

    def __open_mask( self, mask ):
        if mask is None:
            self.__mask_path = None
            return
        if self.__msk is not None:
            self.__msk.close( )
        self.__msk = imagetool( )
        try:
            self.__msk.open(mask)
            self.__mask_path = mask
        except Exception as ex:
            self.__msk = None
            self.__mask_path = None
            raise RuntimeError(f'could not open mask: {mask}') from ex
        mskshape = self.__msk.shape( )
        if self.__img is not None and all(self.__img.shape( ) != mskshape):
            raise RuntimeError(f'mismatch between image shape ({self.__img.shape( )}) and mask shape ({mskshape})')
        if self.__chan_shape is None: self.__chan_shape = list(mskshape[0:2])

    def channel( self, index, slice=None ):
        """Retrieve one channel from the image cube. The `index` should be a
        two element list of integers. The first integer is the ''stokes'' axis
        in the image cube. The second integer is the ''channel'' axis in the
        image cube.

        Parameters
        ----------
        index: [ int, int ]
            list containing first the ''stokes'' index and second the ''channel'' index
        """
        import math as m
        if self.__img is None:
            raise RuntimeError('no image is available')

        floor = lambda x: list(map(m.floor,x)) if isinstance(x,list) else m.floor(x)
        ceil = lambda x: list(map(m.floor,x)) if isinstance(x,list) else m.floor(x)

        blc = floor(slice[0]) if slice else [0,0]
        trc = ceil(slice[1]) if slice else self.__chan_shape

        chan = np.squeeze( self.__img.getchunk( blc=blc + index,
                                                trc=trc + index) )
        cursize = chan.shape[0]*chan.shape[1]

        if cursize > self.__maxpixels:
            print("DOWNSAMPLE HERE")
            print( f'\tblc={blc + index}\ttrc={trc + index}' )
            chan = self.__downsample( chan, self.__find_tile( chan.shape ) )

        self.__pixel_range = { 'x': [ blc[0], trc[0] ],
                               'y': [ blc[1], trc[1] ] }
        print( f'\trange={self.__pixel_range}' )
        #return np.squeeze( self.__img.getchunk( blc=[0,0] + index,
        #                                        trc=self.__chan_shape + index) ).transpose( )
        return chan.transpose( )

    def mask( self, index, modify=False ):
        """Retrieve one channel mask from the mask cube. The `index` should be a
        two element list of integers. The first integer is the ''stokes'' axis
        in the image cube. The second integer is the ''channel'' axis in the
        image cube.

        Parameters
        ----------
        index: [ int, int ]
            list containing first the ''stokes'' index and second the ''channel'' index
        modify: boolean
            If true, it implies that the channel mask is being retrieved for modification
            and updating the channel on disk. If false, it implies that the channel mask
            is being retrieved for display.
        """
        if self.__msk is None:
            raise RuntimeError(f'cannot retrieve mask at {repr(index)} because no mask cube exists')
        return ( np.squeeze( self.__msk.getchunk( blc=[0,0] + index,
                                                trc=self.__chan_shape + index) ).astype(np.bool_).transpose( )
                 if modify == False else
                 np.squeeze( self.__msk.getchunk( blc=[0,0] + index,
                                                trc=self.__chan_shape + index) ) )

    def put_mask( self, index, mask ):
        """Replace one channel mask with the mask specified as the second parameter.
        The `index` should be a two element list of integers. The first integer is the
        ''stokes'' axis in the image cube. The second integer is the ''channel'' axis
        in the image cube. The assumption is that the :code:`mask` parameter was retrieved
        from the mask cube using the :code:`mask(...)` function with the :code:`modify`
        parameter set to :code:`True`.

        Parameters
        ----------
        index: [ int, int ]
            list containing first the ''stokes'' index and second the ''channel'' index
        mask: numpy.ndarray
            two dimensional array to replace the existing mask for the channel specified
            by :code:`index`
        """
        if self.__msk is None:
            raise RuntimeError(f'cannot replace mask at {repr(index)} because no mask cube exists')
        self.__msk.putchunk( blc=[0,0] + index, pixels=mask )

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
        if self.__img is None:
            raise RuntimeError('no image is available')
        result = np.squeeze( self.__img.getchunk( blc=index + [0],
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

    def __downsample( self, chan, shape ):
        from scipy.interpolate import interp2d
        x = np.linspace( 0, 1, chan.shape[0] )
        y = np.linspace( 0, 1, chan.shape[1] )
        cvt = interp2d( y, x, chan, kind="cubic" )
        x2 = np.linspace( 0, 1, shape[0] )
        y2 = np.linspace( 0, 1, shape[1] )
        return cvt( y2, x2 )
        #return cvt( x2, y2 )

        print( '************************************************************' )
        print( f'convert from {chan.shape} to {shape}' )
        print( '************************************************************' )

    def __find_tile( self, image_shape ):
        ### minimum size for sampling
        maxpixels = max( self.__maxpixels, 250*250 )
        ###
        ### find the tile shape to use that is less than the __maxpixels threshold
        ### and generally preserves the dimensionality of the original channel shape
        ###
        from math import ceil
        shape = image_shape[:2]
        if shape[0] * shape[1] < maxpixels:
            return shape
        mindim = min(shape)
        sub_max = mindim
        sub = ceil(max(shape)/2)
        sub_min = 1
        for _ in range(mindim):
            if sub == sub_max:
                break
            pixels = (shape[0]-sub) * (shape[1]-sub)
            if pixels < maxpixels:
                sub_max = sub
            elif pixels > maxpixels:
                sub_min = sub
            else:
                break
            sub = ceil(abs(sub_max + sub_min)/2)
        return [shape[0]-sub,shape[1]-sub]

    def __init__( self, image, *args, mask=None, abort=None, stats=False, maxpixels=None, **kwargs ):
        super( ).__init__( *args, **kwargs, )

        if ct is None:
            raise RuntimeError('cannot open an image because casatools is not available')

        self.__img = None
        self.__msk = None
        resource_manager.reg_at_exit(self, '__del__')
        self._stats = stats
        self.__open_image( image )
        self.__open_mask( mask )
        self.shape = list(self.__img.shape( ))
        self.__session = None
        self.__abort = abort
        self.__maxpixels = maxpixels
        self.__displayed_axes = { 'x': [0,self.shape[0]],
                                  'y': [0,self.shape[1]] }

        if self.__abort is not None and not callable(self.__abort):
            raise RuntimeError('abort function must be callable')

    def __del__(self):
        if self.__rgn:
            self.__rgn.done( )
        if self.__img != None:
            self.__img.close()
            self.__img.done()
            self.__img = None

    def coorddesc( self ):
        ia = imagetool( )
        ia.open(self.__image_path)
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

        reg = self.__rgn.box( [0,0] + index, self.__chan_shape + index )
        ###
        ### This seems like it should work:
        ###
        #      rawstats = self.__img.statistics( region=reg )
        ###
        ### but it does not so we have to create a one-use image tool (see CAS-13625)
        ###
        ia = imagetool( )
        ia.open(self.__image_path)
        rawstats = ia.statistics( region=reg )
        ia.close( )
        return sort_result( { k: singleton([ x.item( ) for x in v ]) if isinstance(v,np.ndarray) else v for k,v in rawstats.items( ) } )

    async def __send_message( self, ws, msg, err="sending*error" ):
        def dump( obj, space=0, sep=", " ):
            if isinstance(obj,dict):
                return "{ " + sep.join( [ f'{key}: {dump(val)}' for key,val in obj.items() ] ) + " }"
            elif isinstance(obj,list):
                vals = [ f'{dump(val)}' for val in obj ]
                if len(vals) > 2:
                    if all( [ x == vals[0] for x in vals ] ):
                        return f'[ {vals[0]} X {len(vals)} ]'
                return "[ " + sep.join( vals ) + " ]"
            else:
                return type(obj).__name__

        try:
            await ws.send(json.dumps(msg))
        except Exception as e:
            print(f'********************{err}********************')
            print(e)
            print('---------------message-that-failed------------------')
            ### often the failure seems to be an ndarray that
            ### cannot be converted to JSON...
            print( dump(msg) )
            print('----------------------------------------------------')

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
                print(f'FETCH-CHANNEL>>> {cmd}')
                if 'slice' in cmd:
                    print( f'''slice\t>>>>>>---> {cmd['slice']}''' )
                chan = self.channel(cmd['index'],cmd['slice'] if 'slice' in cmd else None)
                mask = self.mask(cmd['index'])
                if self._stats:
                    #statistics for the displayed plane of the image cubea
                    statistics = self.statistics( cmd['index'] )
                    msg = { 'id': cmd['id'],
                            # 'stats': pack_arrays(self.__img.statistics( axes=cmd['index'] )),
                            'message': { 'chan': { 'img': [ pack_arrays(chan) ], 'msk': [ pack_arrays(mask) ] },
                                         'stats': { 'labels': list(statistics.keys( )), 'values': pack_arrays(list(statistics.values( ))) } } }
                else:
                    msg = { 'id': cmd['id'],
                            'message': { 'chan': { 'img': [ pack_arrays(chan) ], 'msk': [ pack_arrays(mask) ] } } }

                await self.__send_message( websocket, msg, "first*send" )
                count += 1
            elif cmd['action'] == 'spectra':
                msg = { 'id': cmd['id'],
                        'message': { 'spectrum': pack_arrays( self.spectra(cmd['index']) ) } }
                await self.__send_message( websocket, msg, "second*send" )
            elif cmd['action'] == 'initialize':
                ###
                ### initialize session identifier
                ###
                if self.__session == None:
                    self.__session = cmd['session']
            else:
                print(f"received messate in python with unknown 'action' value: {cmd}")
