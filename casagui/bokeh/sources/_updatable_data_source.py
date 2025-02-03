########################################################################
#
# Copyright (C) 2025
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
#        Internet email: casa-feedback@nrao.edu.
#        Postal address: AIPS++ Project Office
#                        National Radio Astronomy Observatory
#                        520 Edgemont Road
#                        Charlottesville, VA 22903-2475 USA
#
########################################################################
'''Specialization of the Bokeh ``DataSource`` which allows for update via WebSockets.'''

from uuid import uuid4
from sys import stderr
from contextlib import asynccontextmanager
from bokeh.plotting import ColumnDataSource
from bokeh.core.properties import Instance, String, Nullable
from bokeh.models.callbacks import Callback
from bokeh.models import CustomJS
import websockets
from ._data_pipe import DataPipe
from ..state import casalib_url, casaguijs_url
from ...utils import find_ws_address

class UpdatableDataSource(ColumnDataSource):
    """Implementation of a `ColumnDataSource` customized to allow updates from Python via
    WebSockets after the Bokeh GUI has been displayed. This class is derived from `ColumnDataSource`
    and provides an `update` function that can be used to update the plotted data. While this
    is useful when Bokeh is used directly in a Python session, the `stream` function provided
    by `ColumnDataSource` should be used to update plots which are implemented using the Bokeh
    server. This function can be used for plots which may displayed and managed directly from an
    interactive Python session via `asyncio`. However, even in this case it may be more performant
    to include all of the initial plot points when creating the data source. Future updates in
    response to user interaction could be accomplished using this class.

    This class allows the use to specify `js_init` code that is run in the browser when this
    class is initialized there. The JavaScript implementation provides default code which is
    run in the browser when the user calls the `update` function from Python. This code works
    for single dimemsion data by simply appending the supplied updates to the end of the existing
    plot data. If the user supplies an implementation for `js_update` then this code is used
    in preference to the simple, default implementation. In the future the default update
    implementation may be expanded to be more useful for 2D plots.

    Attributes
    ----------
    js_init: CustomJS
        JavaScript code to be run when this DataSource is loaded
    js_update: CustomJS
        JavaScript code to be run to update the data
    pipe: DataPipe
        Optional attribute that allows the user to specify a reused DataPipe
    data:
        INHERITED contains the data provided by this DataSource
    """

    js_init = Nullable(Instance(Callback), help="""
    JavaScript to be run during initialization of an instance of this DataSource object.
    """)

    js_update = Nullable(Instance(Callback), help="""
    JavaScript to be run to update during initialization of an instance of this DataSource object.
    The default behavior is to append to the existing data.
    """)

    pipe = Instance(DataPipe, help="""
    Optional attribute that allows for reusing a single DataPipe for multiple purposes
    """ )

    session_id = String( help="""
    Internal id used for communcations.
    """ )

    __javascript__ = [ casalib_url( ), casaguijs_url( ) ]

    __created_pipe = False
    __id = str(uuid4( ))
    __user_init = None

    def __init__( self, *args,
                  callback=None,
                  **kwargs ):

        ### websocket communication id
        kwargs['session_id'] = self.__id

        if 'pipe' not in kwargs:
            kwargs['pipe'] = DataPipe( address=find_ws_address( ) ) #, abort=abort )
            self.__created_pipe = True
        if 'js_init' in kwargs:
            self.__user_init = kwargs['js_init']

        kwargs['js_init'] = CustomJS( args=dict( userinit=self.__user_init ),
                                      code='''this._data_keys = casalib.reduce(
                                                  (acc,key,value) => {
                                                      if ( Array.isArray(value) ) acc.push( key )
                                                      return acc }, this.data, [ ] )

                                              this.pipe.register( this.session_id,
                                                                  ( msg ) => {
                                                                      // [...array1, ...array2]
                                                                      if ( ! ('data' in msg) )
                                                                          return { result: 'error', msg: 'expected to find "data" in message' }
                                                                      for (const k of this._data_keys) {
                                                                          if ( ! (k in msg.data) )
                                                                              return { result: 'error', msg: `expected "${k}" field in update "data"` }
                                                                      }
                                                                      if ( this.js_update ) {
                                                                          this.js_update.execute( this, { data: msg.data } ).then(
                                                                             (data) => { this.data = data } )
                                                                      } else {
                                                                          const data_update = { }
                                                                          for (const k of this._data_keys) {
                                                                              const existing = this.data[k]
                                                                              const addition = msg.data[k]
                                                                              data_update[k] = [...existing, ...addition]
                                                                          }
                                                                          this.data = data_update
                                                                      }
                                                                      return { result: 'success',
                                                                               msg: casalib.reduce(
                                                                                        (acc,key,value) => {
                                                                                            if ( ! ( key in this.data ) )
                                                                                                acc[key] = value
                                                                                            return acc
                                                                                        }, msg.data, { } ) }
                                                                  } )

                                              window.addEventListener(
                                                  'beforeunload',
                                                  (event) => {
                                                      function send_shutdown(id,pipe) {
                                                          return new Promise((resolve) =>
                                                              pipe.send( id, { action: 'stop' },
                                                                         (msg) => { resolve(msg) } ) )
                                                      }
                                                      send_shutdown(this.session_id,this.pipe).then(
                                                          (result) => { console.log(`Shutdown Result: ${result}`) } )
                                                  } )

                                              if ( userinit != null ) {
                                                  void userinit.execute( this )
                                              }''' )

        super( ).__init__( *args, **kwargs )
        self.__callback = callback
        self.__stop = None

        async def manage_requests( msg, self=self ):
            result = 'OK'
            if self.__stop and 'action' in msg and msg['action'] == 'stop':
                self.__stop( msg )
            elif self.__callback and 'action' in msg and 'message' in msg and msg['action'] == 'callback':
                result = await self.__callback( msg['message'] )
            return { 'result': result }

        self.pipe.register( self.__id, manage_requests )

    async def update( self, data, callback=None ):
        def default_callback( msg, self=self ):
            if msg['result'] == 'error':
                print( f'''UpdatableDataSource Error: {msg['msg']}''', file=stderr )
        await self.pipe.send( self.__id, { 'action': 'append', 'data': data }, default_callback if callback is None else callback )

    @asynccontextmanager
    async def serve( self, stop_function ):
        self.__stop = stop_function
        if not self.__created_pipe:
            raise RuntimeError( 'UpdatableDataSource.serve should only be called for when a "pipe" is NOT supplied as part of initialization' )

        self._stop_serving_function = stop_function
        async with websockets.serve( self.pipe.process_messages, self.pipe.address[0], self.pipe.address[1] ) as msgpipe:
            yield { 'msgpipe': msgpipe }
