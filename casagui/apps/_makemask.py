########################################################################
#
# Copyright (C) 2022
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
'''implementation of the ``MakeMask`` application for interactive creation
of channel masks'''
import asyncio
from contextlib import asynccontextmanager
from bokeh.layouts import row, column
from bokeh.plotting import show
from bokeh.models import Button, CustomJS
from casagui.toolbox import CubeMask
from casagui.bokeh.components import SVGIcon
from bokeh.io import reset_output as reset_bokeh_output
from ..utils import resource_manager, reset_resource_manager

class MakeMask:
    '''Class that can be used to launch a makemask GUI with ``MakeMask('test.image')( )``.'''

    def __stop( self ):
        self.__result_future.set_result(self.__retrieve_result( ))

    def _abort_handler( self, err ):
        self._error_result = err
        self.__stop( )

    def __reset( self ):
        if self.__initialized:
            reset_bokeh_output( )
            reset_resource_manager( )

        ###
        ### reset asyncio result future
        ###
        self.__result_future = None

        ###
        ### used by data pipe (websocket) initialization function
        ###
        self.__initialized = False

        self._cube = CubeMask(self._image_path)
        self._image = None
        ###
        ### error or exception result
        ###
        self._error_result = None

    def __init__( self, image ):
        '''create a ``makemask`` object which will display image planes from a CASA
        image and allow the user to draw masks for each channel.

        Parameters
        ----------
        image: str
            path to CASA image for which interactive masks will be drawn
        '''
        self._image_path = image
        self._cube = CubeMask(self._image_path)
        self._done = None
        self._help = None
        self._help_text = None
        self._layout = None

        ###
        ### This is used to tell whether the websockets have been initialized, but also to
        ### indicate if __call__ is being called multiple times to allow for resetting Bokeh
        ###
        self.__initialized = False

        ###
        ### the asyncio future that is used to transmit the result from interactive clean
        ###
        self.__result_future = None

    def _launch_gui( self ):
        '''create and show GUI
        '''
        self.__initialized = True

        width = 35
        height = 35
        self._done = Button( label="", button_type="danger", max_width=width, max_height=height, name='done',
                             icon=SVGIcon(icon_name='makemask-done', size=1.4) )
        self._help = Button( label="", max_width=width, max_height=height, name='help',
                             icon=SVGIcon(icon_name='help', size=1.4) )

        ### CubeMask provides a help table
        self._help_text = self._cube.help( rows=[ '<tr><td><i>red check button</i></td><td>clicking the red check button will close the dialog and return masks to python</td></tr>' ] )

        self._image = self._cube.image( )
        self._layout = column( self._cube.channel_label( ),
                               self._image,
                               row( self._cube.slider( ), self._help, self._done ),
                               self._help_text )

        self._done.js_on_click( CustomJS( args=dict( obj=self._cube.js_obj( ) ),
                                          code='''obj.done( )''' ) )                  ### CubeMask should return javascript object which contains
                                                                                      ### a done function to stop cube masking
        self._help.js_on_click( CustomJS( args=dict( help=self._help_text ),
                                          code='''if ( help.visible == true ) help.visible = false
                                                  else help.visible = true''' ) )
        self._cube.connect( )
        show(self._layout)

    def _asyncio_loop( self ):
        '''return the event loop which can be mixed in with an existing event loop
        to allow GUI and websocket events to be processed.
        '''
        return self._cube.loop( )

    def __call__( self ):
        '''Display GUI using the event loop specified by ``loop``.
        '''
        async def _run_( ):
            async with self.serve( ) as s:
                await s[0]
        asyncio.run(_run_( ))
        return self.result( )

    @asynccontextmanager
    async def serve( self ):
        '''This function is intended for developers who would like to embed interactive
        clean as a part of a larger GUI. This embedded use of interactive clean is not
        currently supported and would require the addition of parameters to this function
        as well as changes to the interactive clean implementation. However, this function
        does expose the ``asyncio.Future`` that is used to signal completion of the
        interactive cleaning operation, and it provides the coroutines which must be
        managed by asyncio to make the interactive clean GUI responsive.
        '''
        self.__reset( )
        self._launch_gui( )

        async with self._cube.serve( self.__stop ) as cube:
            self.__result_future = asyncio.Future( )
            yield ( self.__result_future, { 'cube': cube } )

    def __retrieve_result( self ):
        '''If InteractiveClean had a return value, it would be filled in as part of the
        GUI dialog between Python and JavaScript and this function would return it'''
        if isinstance(self._error_result,Exception):
            raise self._error_result
        elif self._error_result is not None:
            return self._error_result
        return self._cube.result( )

    def result( self ):
        '''If InteractiveClean had a return value, it would be filled in as part of the
        GUI dialog between Python and JavaScript and this function would return it'''
        if self.__result_future is None:
            raise RuntimeError( 'no interactive clean result is available' )
        return self.__result_future.result( )
