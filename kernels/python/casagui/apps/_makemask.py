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
import asyncio
from bokeh.layouts import row, column
from bokeh.plotting import show
from bokeh.models import Button, CustomJS
from casagui.toolbox import cube_mask
from casagui.bokeh.components.custom_icon.svg_icon import SVGIcon


class makemask:

    def __init__( self, image ):
        '''create a ``makemask`` object which will display image planes from a CASA
        image and allow the user to draw masks for each channel.

        Parameters
        ----------
        image: str
            path to CASA image for which interactive masks will be drawn
        '''
        self._cube = cube_mask(image)

    def _launch_gui( self ):
        '''create and show GUI
        '''
        width = 35
        height = 35
        self._done = Button( label="", button_type="danger", max_width=width, max_height=height, name='done',
                             icon=SVGIcon(icon_name='makemask-done', size=1.4) )
        self._help = Button( label="", max_width=width, max_height=height, name='done',
                             icon=SVGIcon(icon_name='help', size=1.4) )

        self._help_text = self._cube.help( )                                          ### cube_mask provides a help table
        
        self._layout = column( self._cube.image( ),
                               row( self._cube.slider( ), self._help, self._done ),
                               self._help_text )

        self._done.js_on_click( CustomJS( args=dict( obj=self._cube.js_obj( ) ),
                                          code='''obj.done( )''' ) )                  ### cube_mask should return javascript object which contains
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

    def __call__( self, loop=asyncio.get_event_loop( ) ):
        '''Display GUI using the event loop specified by ``loop``.

        Parameters
        ----------
        loop: event loop object
            defaults to standard asyncio event loop.

        Example:
            Create ``iclean`` object and display::

                print( "Result: %s" %
                       iclean( vis='refim_point_withline.ms', imagename='test', imsize=512,
                               cell='12.0arcsec', specmode='cube',
                               interpolation='nearest', ... )( ) )
        '''
        try:
            loop.run_until_complete(self.show( ))
            loop.run_forever( )
        except KeyboardInterrupt:
            print('\nInterrupt received, stopping GUI...')

        return self.result( )

    def show( self ):
        '''Get the makemask event loop to use for running the ``makemask`` GUI
        as part of an external event loop.
        '''
        self._launch_gui( )
        return self._asyncio_loop( )

    def result( self ):
        '''Retrieve the masks that have been drawn by the user. The return
        value is a dictionary with two elements ``masks`` and ``polys``.

        The value of the ``masks`` element is a dictionary that is indexed by
        tuples of ``(stokes,chan)`` and the value of each element is a list
        whose elements describe the polygons drawn on the channel represented
        by ``(stokes,chan)``. Each polygon description in this list has a
        polygon index (``p``) and a x/y translation (``d``).

        The value of the ``polys`` element is a dictionary that is indexed by
        polygon indexes. The value of each polygon index is a dictionary containing
        ``type`` (whose value is either ``'rect'`` or ``'poly``) and ``geometry``
        (whose value is a dictionary containing ``'xs'`` and ``'ys'`` (which are
        the x and y coordinates that define the polygon).
        '''
        return self._cube.result( )