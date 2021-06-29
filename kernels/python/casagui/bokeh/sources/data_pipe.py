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
from bokeh.core.properties import Tuple, String, Int

from ..utils import pack_arrays

import inspect
import threading
import asyncio
import websockets
import json

import numpy as np

class DataPipe(DataSource):

    address = Tuple( String, Int, help="two integer sequence representing the address and port to use for the websocket" )

    __implementation__ = TypeScript( "" )

    def __init__( self, *args, **kwargs ):
        super( ).__init__( *args, **kwargs )
        self.__send_queue = dict( )
        self.__pending = dict( )
        self.__incoming_callbacks = dict( )
        self.__websocket = None
        self.__lock = threading.Lock( )

    def __enqueue_send( self, ident, msg, callback ):
        ### it is assumed that this is called AFTER the lock has been aquired
        if ident in self.__send_queue:
            self.__send_queue[ident].insert(0, { 'cb': callback, 'msg': msg })
        else:
            self.__send_queue[ident] = [ { 'cb': callback, 'msg': msg } ]
    def __dequeue_send( self, ident ):
        ### it is assumed that this is called AFTER the lock has been aquired
        if ident in self.__send_queue:
            if self.__send_queue[ident]:
                return self.__send_queue[ident].pop( )
            else:
                return None
        else:
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
        else:
            return None

    def register( self, ident, callback ):
        ## register callback for requests from javascript -> python
        ## callback will be called for each arriving javascript request
        with self.__lock:
            self.__incoming_callbacks[ident] = callback

    async def send( self, ident, message, callback ):
        ## send new message from python -> javascript
        ## callback will be called with the result
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

    async def process_messages( self, websocket, path ):
        count = 1
        try:
            self.__websocket = websocket
            async for message in websocket:
                msg = json.loads(message)
                with self.__lock:
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
                    else:
                        if msg['id'] not in self.__incoming_callbacks:
                            raise RuntimeError('incoming js request with no callback: %s' % msg)
                        result = self.__incoming_callbacks[msg['id']](msg['message'])
                        await self.__websocket.send(json.dumps({ 'id': msg['id'],
                                                                 'message': pack_arrays(result),
                                                                 'direction': msg['direction'] }))
        finally:
            self.__websocket = None
