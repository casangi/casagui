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
'''Implementation of a general purpose event manager between Python and
JavaScript via ``websockets``. This provides a mechanism like the
``ImagePipe``. The difference is that ``ImagePipe`` is tuned for use
with CASA images but ``DataPipe`` can have generic messages.'''

import inspect
import threading
import asyncio
import json

from bokeh.models.sources import DataSource
from bokeh.util.compiler import TypeScript
from bokeh.core.properties import Tuple, String, Int, Instance, Nullable
from bokeh.models.callbacks import Callback

from ..utils import pack_arrays

class DataPipe(DataSource):
    """This class allows for communication between Python and the JavaScript implementation
    running in a browser. It allows Python code to send a message to JavaScript and register
    a callback which will receive the result. JavaScript code can do the same to request
    information from Python. Generally messages are expected to be dictionaries in the
    Python domain and objects in the JavaScript domain. UUIDs are used to keep messages in
    sync, and messages sent with the same UUID are queued until the currently pending
    message reply is recieved. A class can use multipe UUIDs to control queuing behavior.

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

    init_script = Nullable(Instance(Callback), help="""
    JavaScript to be run during initialization of an instance of an DataPipe object.
    """)

    address = Tuple( String, Int, help="two integer sequence representing the address and port to use for the websocket" )

    __implementation__ = TypeScript( "" )

    def __init__( self, *args, abort=None, **kwargs ):
        super( ).__init__( *args, **kwargs )
        self.__send_queue = { }
        self.__pending = { }
        self.__incoming_callbacks = { }
        self.__websocket = None
        self.__lock = threading.Lock( )
        self.__session = None
        self.__abort = abort

        if self.__abort is not None and not callable(self.__abort):
                raise RuntimeError(f'abort function must be callable ({type(self.__abort)} is not)')

    def __enqueue_send( self, ident, msg, callback ):
        ### it is assumed that this is called AFTER the lock has been aquired
        if ident in self.__send_queue:
            self.__send_queue[ident].insert(0, { 'cb': callback, 'msg': msg })
        else:
            self.__send_queue[ident] = [ { 'cb': callback, 'msg': msg } ]
    def __dequeue_send( self, ident ):
        ### it is assumed that this is called AFTER the lock has been aquired
        if ident in self.__send_queue and self.__send_queue[ident]:
            return self.__send_queue[ident].pop( )
        return None
    async def __put_pending( self, ident, callback ):
        ### it is assumed that this is called AFTER the lock has been aquired
        ## info about request sent to javascript waits in this queue
        ## until the javascript reply is received...
        if ident in self.__pending:
            if self.__websocket is not None:
                await self.__websocket.send( { 'id': '', 'message': 'queueing callback, but already one callback waiting', 'direction': 'error' } )
        else:
            self.__pending[ident] = callback

    def __get_pending( self, ident ):
        ### it is assumed that this is called AFTER the lock has been aquired
        ## when reply arrives for a request to javascript
        ## the callback is retrieved from the waiting queue
        if ident in  self.__pending:
            result = self.__pending[ident]
            del self.__pending[ident]
            return result
        return None

    def register( self, ident, callback ):
        """Register a callback to handle all requests coming from JavaScript. The
        callback will be called whenever a request arrives.

        Parameters
        ----------
        ident: string
            UUID which is associated with the messages that should be delivered
            to this callback
        callback: (string) => dictionary
            Callback which receives the message from Python as its sole parameter.
            The return value of this callback is delivered to the JavaScript code
            as the ''reply'' to to JavaScript in response to the ''request'' contained
            in the message.
        """
        with self.__lock:
            self.__incoming_callbacks[ident] = callback

    async def send( self, ident, message, callback ):
        """Send a `message` to JavaScript identified by `ident`. Once the reply is
        received, the `callback` will be called with the reply message.

        Parameters
        ----------
        ident: string
            UUID to associate with this message. It is used to keep track of the callback
            that should be called when the reply is received.
        message: dictionary
            This dictionary contains the request for the JavaScript code.
        callback: (string) => void
            Callback which receives the message that JavaScript generates in response to
            the request contained in the `message` parameter.
        """
        with self.__lock:
            if self.__websocket is not None:
                msg = { 'id': ident, 'message': pack_arrays(message), 'direction': 'p2j' }
                if ident in self.__pending:
                    self.__enqueue_send( ident, msg, callback )
                else:
                    if ident in self.__send_queue and self.__send_queue[ident]:
                        self.__enqueue_send( ident, msg, callback )
                        existing = self.__dequeue_send(ident)
                        self.__put_pending(ident, existing['cb'])
                        await self.__websocket.send(json.dumps( existing['msg'] ))
                    else:
                        await self.__put_pending(ident, callback)
                        await self.__websocket.send(json.dumps( msg ))

    async def process_messages( self, websocket ):
        """Process messages related to image display updates.

        Parameters
        ----------
        websocket: websocket object
            Websocket serve function passes in the websocket object to use.
        path:
            Websocket serve provides a second parameter.
        """
        try:
            self.__websocket = websocket
            async for message in websocket:
                msg = json.loads(message)
                if 'session' not in msg:
                    await self.__websocket.close( )
                    err = RuntimeError(f'session not in: {msg}')
                    if self.__abort is not None:
                        self.__abort( asyncio.get_running_loop( ), err )
                    else:
                        raise err
                    return
                elif self.__session != None and self.__session != msg['session']:
                    await self.__websocket.close( )
                    err = RuntimeError(f"session corruption: {msg['session']} does not equal {self.__session}")
                    if self.__abort is not None:
                        self.__abort( asyncio.get_running_loop( ), err )
                    else:
                        raise err
                    return

                with self.__lock:
                    ###
                    ### initialize session identifier
                    ###
                    if self.__session == None:
                        self.__session = msg['session']
                    if msg['direction'] == 'p2j':
                        cb = self.__get_pending(msg['id'])
                        outgo = self.__dequeue_send(msg['id'])
                        if outgo is not None:
                            await websocket.send(json.dumps(outgo['msg']))
                            self.__put_pending(msg['id'],outgo['cb'])
                        if cb is not None:
                            if inspect.isawaitable(cb):
                                await cb(msg['message'])
                            else:
                                cb(msg['message'])
                    elif msg['id'] != 'initialize':
                        ###
                        ### no cb/reply for initialization of session
                        ###
                        if msg['id'] not in self.__incoming_callbacks:
                            raise RuntimeError(f'incoming js request with no callback: {msg}')
                        result = self.__incoming_callbacks[msg['id']](msg['message'])
                        if inspect.isawaitable(result):
                            await self.__websocket.send(json.dumps({ 'id': msg['id'],
                                                                     #'message': pack_arrays(await result),
                                                                     'message': pack_arrays(await result),
                                                                     'direction': msg['direction'] }))
                        else:
                            await self.__websocket.send(json.dumps({ 'id': msg['id'],
                                                                     'message': pack_arrays(result),
                                                                     'direction': msg['direction'] }))
        finally:
            self.__websocket = None
