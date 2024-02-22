#######################################################################
#
# Copyright (C) 2022,2023,2024
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
'''This provides an implementation of ``CubeMask`` which allows interactive
clean and makemask to share a common implementaton. The user calls member
functions to create widgets which can be placed in the GUI created by the
calling application. Once all of the widgets have been created. The
``connect`` member function creates all of the Bokeh/JavaScript callbacks
that allow the widgets to interact'''

import math
from os import path
import asyncio
from uuid import uuid4
from sys import platform
from os.path import dirname, join
import websockets
from contextlib import asynccontextmanager
from bokeh.events import SelectionGeometry, MouseEnter, MouseLeave, LODStart, LODEnd, ValueSubmit
from bokeh.models import CustomJS, CustomAction, Slider, PolyAnnotation, Div, Span, HoverTool, TableColumn, \
                         DataTable, Select, ColorPicker, Spinner, Select, Button, PreText, Dropdown, \
                         LinearColorMapper, TextInput, Spacer, InlineStyleSheet, Quad
from bokeh.models import WheelZoomTool, PanTool, ResetTool, PolySelectTool
from bokeh.models import BasicTickFormatter
from bokeh.plotting import ColumnDataSource, figure
from casagui.bokeh.sources import ImageDataSource, ImagePipe, DataPipe
from casagui.bokeh.format import WcsTicks
from casagui.bokeh.models import EditSpan
from ..utils import pack_arrays, find_ws_address, set_attributes, resource_manager, polygon_indexes, is_notebook, image_as_mime
from ..bokeh.models import EvTextInput
from ..bokeh.tools import CBResetTool
from ..bokeh.state import available_palettes, find_palette, default_palette
from bokeh.layouts import row, column
from bokeh.models.dom import HTML
from bokeh.models import Tooltip
from ..bokeh.models import TipButton, Tip
from casagui.bokeh.utils import svg_icon

import numpy as np

class CubeMask:
    '''Class which provides a common implementation of Bokeh widget behavior for
    interactive clean and make mask'''

    def __init__( self, image, mask=None, abort=None ):
        '''Create a cube masking GUI which includes the 2-D raster cube plane display
        along with these optional components:

        *  slider to move through planes
        *  spectrum plot (in response to mouse movements in 2-D raster display)
        *  statistics (table)

        Parameters
        ----------
        image: str
            path to CASA image for which interactive masks will be drawn
        mask: str or None
            If provided, this shifts the masking to bitmask operation. In
            bitmask operation, the drawn regions are used to add or subtract
            from a bitmask cube image instead of being the union of all drawn
            regions. This is the standard mode of operation for interactive clean.
        abort: function
            If provided, the ``abort`` function will be called in the case of an error.
        '''
        self._is_notebook = is_notebook()
        self._color = '#00FF00'                            # default color for mask, selection, etc.
        self._stop_serving_function = None                 # function supplied when starting serving
        self._image_path = image                           # path to image cube to be displayed
        self._mask_path = mask                             # path to bitmask cube (if any)
        self._mask_id = None                               # id for each unique mask
        self._image = None                                 # figure displaying cube & mask planes
        self._channel_ctrl = None                          # display channel and stokes
        self._stokes_labels = None                         # stokes labels for the image cube
        self._channel_ctrl_stokes_dropdown = None          # drop down for changing stokes when _channel_ctrl is used
        self._channel_ctrl_group = None                    # row for channel control group
        self._coord_ctrl_dropdown = None                   # select pixel or world
        self._coord_ctrl_group = None                      # row for coordinate control group
        self._status_div = None                            # status line (used to report problems)
        self._pixel_tracking_text = None                   # cursor tracking pixel value
        self._chan_image = None                            # channel image
        self._bitmask = None                               # bitmask image
        self._bitmask_contour = None                       # bitmask MultiPolygon contour
        self._bitmask_contour_ds = None                    # bitmask MultiPolygon contour data source
        self._bitmask_color_selector = None                # bitmask color selector
        self._bitmask_transparency_button = None           # select whether the 1s or 0s is transparent
        self._bitmask_contour_maskmod = None               # display mask contour as a region MultiPolygon (for copy/paste)
        self._bitmask_contour_maskmod_ds = None            # display mask contour data source
        self._mask0 = None                                 # INTERNAL systhesis imaging mask
        self._goto = None                                  # goto channel row (contains text input and dropdown)
        self._goto_txt = None                              # goto channel text input
        self._goto_stokes = None                           # goto channel stokes dropdown
        self._slider = None                                # slider to move from plane to plane
        self._slider_callback = None                       # called after the channel update for slider movement is complete
        self._tapedeck = None                              # buttons to move the slider
        self._spectrum = None                              # figure displaying spectrum along the frequency axis
        self._statistics = None                            # statistics data table
        self._statistics_mask = None                       # button to switch from channel statistics to mask statistics
        self._statistics_use_mask = False                  # whether statistics calculations will be based on the masked
                                                           # area or the whole channel
        self._palette = None                               # palette selection
        self._help_button = None                           # help button that creates a new tab/window (instead of hide/show Div)
        self._image_spectrum = None                        # spectrum data source
        self._image_source = None                          # ImageDataSource
        self._statistics_source = None
        self._pipe = { 'image': None, 'control': None }    # data pipes
        self._ids = { 'palette': str(uuid4( )),
                      'mask-mod': str(uuid4( )),
                      'done': str(uuid4( )),
                      'config-statistics': str(uuid4( )),
                      'fetch-spectrum': str(uuid4( )),
                      'colormap-adjust': str(uuid4( )) } # ids used for control messages

        ###########################################################################################################################
        ### JavaScript init script to be run early in the startup. Piggybacked off of the ImagePipe initialization              ###
        ### CustomAction callbacks are set in connect( ) function.                                                              ###
        ###########################################################################################################################
        _add_ = dict( chan=image_as_mime(join( dirname(dirname(__file__)), "__icons__", 'add-chan.png' ) ),
                      cube=image_as_mime(join( dirname(dirname(__file__)), "__icons__", 'add-cube.png' ) ) )
        _sub_ = dict( chan=image_as_mime(join( dirname(dirname(__file__)), "__icons__", 'sub-chan.png' ) ),
                      cube=image_as_mime(join( dirname(dirname(__file__)), "__icons__", 'sub-cube.png' ) ) )
        self._mask_icons_ = dict( on=image_as_mime(join( dirname(dirname(__file__)), "__icons__", 'new-layer-sm-selected.png' ) ),
                                  off=image_as_mime(join( dirname(dirname(__file__)), "__icons__", 'new-layer-sm.png' ) ) )
        self._mask_add_sub = { 'add': CustomAction( icon=_add_['chan'],
                                                    description="add region to current channel's mask (hold Shift key then click to add to all channels)" ),
                               'sub': CustomAction( icon=_sub_['chan'],
                                                    description="subtract region from current channel's mask (hold Shift key then click to subtract from all channels)" ),
                               'mask': CustomAction( icon=self._mask_icons_['off'],
                                                     description="select the mask for the current channel" ),
                               'img': dict( add=_add_, sub=_sub_ ) }

        self._fig = { }
        self._hover = { 'spectrum': None, 'image': None }   # HoverTools which are used to synchronize image/spectrum
                                                           # movement/taps and and corresponding display

        self._result = None                                # result to be filled in from Bokeh

        self._image_server = None
        self._control_server = None

        self._cb = { }
        self._annotations = [ ]		                # statically allocate fixed poly annotations for (re)use
                                                        # on successive image cube planes

        self._cm_adjust = { 'id': self._ids['colormap-adjust'],
                            'bins': 256 }               # state for colormap_adjust(...)

        self.__abort = abort

        if self.__abort is not None and not callable(self.__abort):
            raise RuntimeError('abort function must be callable')

        ###########################################################################################################################
        ### Notes on States                                                                                                     ###
        ###                                                                                                                     ###
        ### Global state is tied to the ImageDataSource                                                                         ###
        ###                                                                                                                     ###
        ###    selection buffer:  tied to per-channel state                                                                     ###
        ###    copy buffer:       global                                                                                        ###
        ###########################################################################################################################
        self._js_mode_code = {
                   'bitmask-hotkey-setup-add-sub':    '''
                                              function mask_mod_result( msg ) {
                                                  if ( msg.result == 'success' ) {
                                                      if ( 'update' in msg && 'clear_region' in msg.update && msg.update.clear_region ) {
                                                          /* if the src mask on disk has changed the maskmod region is no longer valid */
                                                          maskmod_region_clear( )
                                                      }
                                                      source.refresh( msg => { if ( 'stats' in msg ) { source.update_statistics( msg.stats ) } } )
                                                  }
                                              }
                                              function mask_add_chan( ) {
                                                  if ( annotations[0].xs.length > 0 && annotations[0].ys.length > 0 ) {
                                                      ctrl.send( ids['mask-mod'],
                                                                 { scope: 'chan',
                                                                   action: 'addition',
                                                                   value: { chan: source.cur_chan,
                                                                            xs: annotations[0].xs,
                                                                            ys: annotations[0].ys } },
                                                                 mask_mod_result )
                                                  } else if ( ! casalib.is_empty(mask_region_ds.data.xs) && ! casalib.is_empty(mask_region_ds.data.ys) ) {
                                                      ctrl.send( ids['mask-mod'],
                                                                 { scope: 'chan',
                                                                   action: 'addition',
                                                                   value: { chan: source.cur_chan,
                                                                            src: mask_region_ds._src_chan } },
                                                                 mask_mod_result )
                                                  } else if ( status ) status.text = '<p>no region found</p>'
                                              }
                                              function mask_sub_chan( ) {
                                                  if ( annotations[0].xs.length > 0 && annotations[0].ys.length > 0 ) {
                                                      ctrl.send( ids['mask-mod'],
                                                                 { scope: 'chan',
                                                                   action: 'subtract',
                                                                   value: { chan: source.cur_chan,
                                                                            xs: annotations[0].xs,
                                                                            ys: annotations[0].ys } },
                                                                 mask_mod_result )
                                                  } else if ( ! casalib.is_empty(mask_region_ds.data.xs) && ! casalib.is_empty(mask_region_ds.data.ys.length) ) {
                                                      ctrl.send( ids['mask-mod'],
                                                                 { scope: 'chan',
                                                                   action: 'subtract',
                                                                   value: { chan: source.cur_chan,
                                                                            src: mask_region_ds._src_chan } },
                                                                 mask_mod_result )
                                                  } else if ( status ) status.text = '<p>no region found</p>'
                                              }
                                              function mask_add_cube( ) {
                                                  if ( annotations[0].xs.length > 0 && annotations[0].ys.length > 0 ) {
                                                      ctrl.send( ids['mask-mod'],
                                                                 { scope: 'cube',
                                                                   action: 'addition',
                                                                   value: { chan: source.cur_chan,
                                                                            xs: annotations[0].xs,
                                                                            ys: annotations[0].ys } },
                                                                 mask_mod_result )
                                                  } else if ( ! casalib.is_empty(mask_region_ds.data.xs) && ! casalib.is_empty(mask_region_ds.data.ys) ) {
                                                      ctrl.send( ids['mask-mod'],
                                                                 { scope: 'cube',
                                                                   action: 'addition',
                                                                   value: { chan: source.cur_chan,
                                                                            src: mask_region_ds._src_chan } },
                                                                 mask_mod_result )
                                                  } else if ( status ) status.text = '<p>no region found</p>'
                                              }
                                              function mask_sub_cube( ) {
                                                  if ( annotations[0].xs.length > 0 && annotations[0].ys.length > 0 ) {
                                                      ctrl.send( ids['mask-mod'],
                                                                 { scope: 'cube',
                                                                   action: 'subtract',
                                                                   value: { chan: source.cur_chan,
                                                                            xs: annotations[0].xs,
                                                                            ys: annotations[0].ys } },
                                                                 mask_mod_result )
                                                  } else if ( ! casalib.is_empty(mask_region_ds.data.xs) && ! casalib.is_empty(mask_region_ds.data.ys) ) {
                                                      ctrl.send( ids['mask-mod'],
                                                                 { scope: 'cube',
                                                                   action: 'subtract',
                                                                   value: { chan: source.cur_chan,
                                                                            src: mask_region_ds._src_chan } },
                                                                 mask_mod_result )
                                                  } else if ( status ) status.text = '<p>no region found</p>'
                                              }''',
                   'bitmask-hotkey-setup':    '''
                                              function state_translate_selection( dx, dy ) {
                                                  const shape = source.image_source.shape
                                                  // regions can move out of image, later outlier images may be included
                                                  if ( dx !== 0 ) annotations[0].xs = annotations[0].xs.map( x => x + dx )
                                                  if ( dy !== 0 ) annotations[0].ys = annotations[0].ys.map( y => y + dy )
                                              }
                                              function freeze_cursor_update( ) {
                                                  ctrl._freeze_cursor_update = true
                                              }
                                              casalib.hotkeys( 'escape', { scope: 'channel' },
                                                               (e) => { e.preventDefault( )
                                                                        maskmod_region_clear( ) } )
                                              casalib.hotkeys( 'f', { scope: 'channel' },
                                                               (e) => freeze_cursor_update( ) )
                                              casalib.hotkeys( 'a', { scope: 'channel' },
                                                               (e) => mask_add_chan( ) )
                                              casalib.hotkeys( 's', { scope: 'channel' },
                                                               (e) => mask_sub_chan( ) )
                                              casalib.hotkeys( 'shift+a', { scope: 'channel' },
                                                               (e) => { e.preventDefault( )
                                                                        mask_add_cube( ) } )
                                              casalib.hotkeys( 'shift+s', { scope: 'channel' },
                                                               (e) => { e.preventDefault( )
                                                                        mask_sub_cube( ) } )
                                              casalib.hotkeys( 'shift+`', { scope: 'channel' },
                                                               (e) => { e.preventDefault( )
                                                                        ctrl.send( ids['mask-mod'],
                                                                                   { scope: 'chan',
                                                                                     action: 'not',
                                                                                     value: { chan: source.cur_chan } },
                                                                                   mask_mod_result ) } )
                                              casalib.hotkeys( 'shift+1', { scope: 'channel' },
                                                               (e) => { e.preventDefault( )
                                                                        ctrl.send( ids['mask-mod'],
                                                                                   { scope: 'cube',
                                                                                     action: 'not',
                                                                                     value: { chan: source.cur_chan } },
                                                                                   mask_mod_result ) } )
                                               // move selection set up one pixel  -- bitmask-cube mode
                                               casalib.hotkeys( 'up', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         state_translate_selection( 0, 1 ) } )
                                               // move selection set up several pixel -- bitmask-cube mode
                                               casalib.hotkeys( 'shift+up', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         const shape = source.image_source.shape
                                                                         state_translate_selection( 0, Math.floor(shape[1]/10 ) ) } )
                                               // move selection set down one pixel -- bitmask-cube mode
                                               casalib.hotkeys( 'down', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         state_translate_selection( 0, -1 ) } )
                                               // move selection set down several pixel -- bitmask-cube mode
                                               casalib.hotkeys( 'shift+down', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         const shape = source.image_source.shape
                                                                         state_translate_selection( 0, -Math.floor(shape[1]/10 ) ) } )
                                               // move selection set left one pixel -- bitmask-cube mode
                                               casalib.hotkeys( 'left', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         state_translate_selection( -1, 0 ) } )
                                               // move selection set left several pixel -- bitmask-cube mode
                                               casalib.hotkeys( 'shift+left', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         const shape = source.image_source.shape
                                                                         state_translate_selection( -Math.floor(shape[0]/10 ), 0 ) }  )
                                               // move selection set right one pixel -- bitmask-cube mode
                                               casalib.hotkeys( 'right', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         state_translate_selection( 1, 0 ) } )
                                               // move selection set right several pixel -- bitmask-cube mode
                                               casalib.hotkeys( 'shift+right', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         const shape = source.image_source.shape
                                                                         state_translate_selection( Math.floor(shape[0]/10 ), 0 ) } )
                                              ''',
                   'no-bitmask-hotkey-setup': '''// next region -- no-bitmask-cube mode
                                               casalib.hotkeys( 'alt+]', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         state_next_cursor( )} )
                                               // prev region -- no-bitmask-cube mode
                                               casalib.hotkeys( 'alt+[', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         state_prev_cursor( )} )
                                               // add region to selection -- no-bitmask-cube mode
                                               casalib.hotkeys( 'alt+space, alt+/', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         state_cursor_to_selection( curmasks( ) ) } )
                                               // clear selection -- no-bitmask-cube mode
                                               casalib.hotkeys( 'alt+escape', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         state_clear_selection( ) } )
                                               // delete region identified by cursor -- no-bitmask-cube mode
                                               casalib.hotkeys( 'alt+del,alt+backspace', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         state_remove_mask( ) } )
                                               // move selection set up one pixel  -- no-bitmask-cube mode
                                               casalib.hotkeys( 'up', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         state_translate_selection( 0, 1 ) } )
                                               // move selection set up several pixel -- no-bitmask-cube mode
                                               casalib.hotkeys( 'shift+up', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         const shape = source.image_source.shape
                                                                         state_translate_selection( 0, Math.floor(shape[1]/10 ) ) } )
                                               // move selection set down one pixel -- no-bitmask-cube mode
                                               casalib.hotkeys( 'down', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         state_translate_selection( 0, -1 ) } )
                                               // move selection set down several pixel -- no-bitmask-cube mode
                                               casalib.hotkeys( 'shift+down', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         const shape = source.image_source.shape
                                                                         state_translate_selection( 0, -Math.floor(shape[1]/10 ) ) } )
                                               // move selection set left one pixel -- no-bitmask-cube mode
                                               casalib.hotkeys( 'left', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         state_translate_selection( -1, 0 ) } )
                                               // move selection set left several pixel -- no-bitmask-cube mode
                                               casalib.hotkeys( 'shift+left', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         const shape = source.image_source.shape
                                                                         state_translate_selection( -Math.floor(shape[0]/10 ), 0 ) }  )
                                               // move selection set right one pixel -- no-bitmask-cube mode
                                               casalib.hotkeys( 'right', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         state_translate_selection( 1, 0 ) } )
                                               // move selection set right several pixel -- no-bitmask-cube mode
                                               casalib.hotkeys( 'shift+right', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         const shape = source.image_source.shape
                                                                    state_translate_selection( Math.floor(shape[0]/10 ), 0 ) } )

                                               // copy selection -- no-bitmask-cube mode
                                               casalib.hotkeys( 'alt+c', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         state_copy_selection( )} )

                                               // paste selection current channel -- no-bitmask-cube mode
                                               casalib.hotkeys( 'alt+v', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         register_mask_change('v')
                                                                         state_paste_selection( ) } )

                                               // paste selection to all channels -- no-bitmask-cube mode
                                               casalib.hotkeys( 'alt+shift+v', { scope: 'channel' },
                                                                (e) => { e.preventDefault( )
                                                                         register_mask_change('V')
                                                                         for ( let stokes=0; stokes < source._chanmasks.length; ++stokes ) {
                                                                             for ( let chan=0; chan < source._chanmasks[stokes].length; ++chan ) {
                                                                                 if ( stokes != source._copy_buffer[1][0] ||
                                                                                      chan != source._copy_buffer[1][1] )
                                                                                     state_paste_selection( curmasks( [ stokes, chan ] ) )
                                                                             }
                                                                         } } )

                                               // initialize for cursor operations -- no-bitmask-cube mode
                                               casalib.hotkeys( '*', { keyup: true, scope: 'channel' },
                                                                (e,handler) => { if ( e.type === 'keydown' ) {
                                                                                     if ( (e.key === 'Alt' || e.key == 'Meta') && ! casalib.hotkeys.control )
                                                                                         state_initialize_cursor( )
                                                                                     if ( e.key === 'Control' && casalib.hotkeys.option )
                                                                                         state_clear_cursor( curmasks( ) )
                                                                                 }
                                                                                 if ( e.type === 'keyup' ) {
                                                                                     if ( e.key === 'Alt' || e.key == 'Meta' )
                                                                                         state_clear_cursor( )
                                                                                     if ( e.key === 'Control' && casalib.hotkeys.option )
                                                                                         state_initialize_cursor( )
                                                                                 } } )''',
            'no-bitmask-init':          '''if ( typeof(source._mask_breadcrumbs) === 'undefined' ) {
                                               source._mask_breadcrumbs = ''
                                           }
                                           if ( typeof(source._cur_chan_prev) === 'undefined' ) {
                                               source._cur_chan_prev = source.cur_chan
                                           }
                                           if ( typeof(source._polys) === 'undefined' ) {
                                               source._polys = [ ]              //  [ { id: int,
                                                                                //      type: string,
                                                                                //      geometry: { xs: [ float, ... ], ys: [ float, ... ] } } ]
                                               source._cursor_color = 'white'
                                               source._default_color = 'black'
                                               source._annotation_ids = annotations.reduce( (acc,c) => { acc.push(c.id); return acc }, [ ] )
                                               source._annotations = annotations.reduce( (acc,c) => { acc[c.id] = c; return acc }, { } )
                                                                                // OPT sets the cursor on the first poly
                                               source._cursor = -1              // OPT-n or OPT-p move the _cursor through polys for current channel
                                                                                // OPT-SPACE adds cursor to _selections
                                                                                // OPT-c copies _selections to the _copy_buffer and clears _selections
                                                                                // OPT-v pastes _copy_buffer to a new channel
                                                                                // OPT-SHIFT-v pastes _copy_buffer to ALL channels
                                                                                // OPT-up moves _selections up
                                                                                // OPT-down moves _selections down
                                                                                // OPT-left moves _selections left
                                                                                // OPT-right moves _selections right
                                                                                // OPT-delete removes mask highlighted by _cursor
                                                                                // OPT-CTRL-up moves to next channel
                                                                                // OPT-CTRL-down moves to previous channel
                                                                                // OPT-CTRL-left moves to previous stokes channel
                                                                                // OPT-CTRL-right moves to next stokes channel
                                           }
                                           if ( typeof(source._copy_buffer) === 'undefined' ) {
                                               // Buffer that will contain copied selection so that the selection from one channel can be pasted
                                               // into this channel, another channel, or multiple channels...
                                               //              vvvvvvvvvv------------------------------------------- polygon index to be pasted
                                               //        [ [ [ POLY-INDEX, [ dx, dy ] ], ... ], [ stokes, chan ] ]
                                               //                          ^^^^^^^^^^           ^^^^^^^^^^^^^^^^---- image plane origin of copy
                                               //                                   |
                                               //                                   +------------------------------- x,y delta translation for the copied poly
                                               // The poly index _copy_buffer[0][X] is the polygon that should be pasted and
                                               // the translation _copy_buffer[1][X] is the translation that should be applied
                                               // to the pasted polygon (using a newly aquired annotation from the cache)
                                               source._copy_buffer = [ [ ], [ ] ]
                                           }
                                           if ( typeof(source._chanmasks) === 'undefined' ) {
                                               // Primary axis:   stokes
                                               // Secondary axis: frequency                vvvvvvvvvvvvvvvvvvv------ polygons drawn on this channel
                                               //                 [ [ [ANNOTATION-ID, ... ], [ POLY-INDEX, ... ], [ [ dx, dy ], ... ], [ INDEX, ... ], CHAN ], ... ]
                                               //                     ^^^^^^^^^^^^^^^^^^^^^                       ^^^^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^---- selection indexes
                                               //                                         |                                         |                     (INDEX into previous 3 lists)
                                               //                                         |                                         +------ x,y delta translation
                                               //                                         |
                                               //                                         +--------------------------- annotations in use for this channel
                                               //                                                                      one for each polygon
                                               //
                                               //                 one-to-one correspondence between annotation and poly indexes
                                               source._chanmasks = [ ]
                                               let stokes = source.num_chans[0]
                                               while(stokes-- > 0) {
                                                   source._chanmasks[stokes] = [ ]
                                                   let chan = source.num_chans[1]
                                                   while(chan-- > 0) source._chanmasks[stokes][chan] = [ [ ], [ ], [ ], [ ], [ stokes, chan ] ]
                                               }
                                           }''',
            'no-bitmask-tool-selection':'''if ( source._masking_enabled ) {
                                                               let cm = curmasks( )
                                                               const geometry = cb_obj['geometry']
                                                               if ( geometry.type === 'rect' ) {
                                                                   let poly = newpoly( cm )
                                                                   if ( poly !== null ) {
                                                                       register_mask_change('r')
                                                                       poly[1].type = 'rect'
                                                                       poly[1].geometry.xs = [ geometry.x0, geometry.x0, geometry.x1, geometry.x1 ]
                                                                       poly[1].geometry.ys = [ geometry.y0, geometry.y1, geometry.y1, geometry.y0 ]
                                                                       poly[0].xs = poly[1].geometry.xs
                                                                       poly[0].ys = poly[1].geometry.ys
                                                                       cm[2].push( [0,0] )                               // translation for this polygon
                                                                   }
                                                               } else if ( geometry.type === 'poly' && cb_obj.final ) {
                                                                   let poly = newpoly( cm )
                                                                   if ( poly !== null ) {
                                                                       register_mask_change('p')
                                                                       poly[1].type = 'poly'
                                                                       poly[1].geometry.xs = [ ].slice.call(geometry.x)
                                                                       poly[1].geometry.ys = [ ].slice.call(geometry.y)
                                                                       poly[0].xs = poly[1].geometry.xs
                                                                       poly[0].ys = poly[1].geometry.ys
                                                                       cm[2].push( [0,0] )
                                                                   }
                                                               }
                                                           }'''
        }

        def span_update( span1, span2 ):
            return f'''if ( ! {span1}._edited ) {{
                           {span1}._editing = true
                           if ( {span1}.location <= {span2}.location ) {{
                               {span1}.location = histogram.data_source.data.left[0]
                               min.value = {span1}.location.toString( )
                           }} else {{
                               {span1}.location = histogram.data_source.data.right[histogram.data_source.data.right.length-1]
                               max.value = {span1}.location.toString( )
                           }}
                           {span1}._editing = false
                       }}
                       '''

        self._js = { ### update stats in response to channel changes
                     ### -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
                     ### The slider and the events from the update of the image source are
                     ### coupled because the image cube channel can be changed outside of the
                     ### slider context.
                     ###
                     ###   (1) moving the slider updates the channel
                     ###   (2) when the channel is changed using a hotkey the slider must be updated
                     ###
                     ### to fix a problem where moving the slider very quickly caused oscillation between
                     ### two slider values (slider would just cycle back and forth) these two related
                     ### updates are separated by the hotkeys scope. When the scope is 'channel' then
                     ### the cursor is inside, hotkeys are active (and slider is updated). When outside
                     ### and the scope is not equal to 'channel', the slider updates the channel.
                     ###
                     'pixel-update-func': ''' function refresh_pixel_display( index, intensity, masked, world_coord=true ) {
                                                  const digits = 5
                                                  if ( world_coord ) {
                                                      const pt = new casalib.coordtxl.Point2D( Number(index[0]), Number(index[1]) )
                                                      isource.wcs( ).imageToWorldCoords(pt,false)
                                                      let wcstr = new casalib.coordtxl.WorldCoords(pt.getX(),pt.getY()).toString( )
                                                      pixlabel.text = '<p ALIGN=RIGHT>' + wcstr + "</p><p ALIGN=RIGHT>" + intensity.toExponential(digits) +
                                                                      (masked ? " <b>masked</b>" : " <b>unmasked</b>") + '</p>'
                                                  } else {
                                                      pixlabel.text = '<p ALIGN=RIGHT>' + index[0] + ', ' + Number(index[1]) +
                                                                      "</p><p ALIGN=RIGHT>" + intensity.toExponential(digits) +
                                                                      (masked ? " <b>masked</b>" : " <b>unmasked</b>") + '</p>'
                                                  }
                                              }
                                              function update_spectrum( _chan, _index, update_func ) {
                                                  function array_equal( a1, a2 ) {
                                                      return (a1.length == a2.length) && a1.every((element, index) => element === a2[index])
                                                  }
                                                  if ( isource._update_spectrum &&
                                                       _chan[0] == isource._update_spectrum.chan[0] &&
                                                       array_equal( _index, isource._update_spectrum.index ) ) {
                                                      update_func( { ...isource._update_spectrum, chan: _chan } )
                                                  } else {
                                                      function _update_spectrum ( msg ) {
                                                          if ( msg.update &&
                                                               'spectrum' in msg.update &&
                                                               'index' in msg.update &&
                                                               'chan' in msg.update &&
                                                               msg.update.index.length == 2 &&
                                                               msg.update.index.length == 2 ) {
                                                              const { spectrum, chan, index, mask } = msg.update
                                                              isource._update_spectrum = { spectrum, mask, chan, index }
                                                              update_func( isource._update_spectrum )
                                                          } else console.log( 'Error: update of spectrum', msg )
                                                      }
                                                      if ( isource._current_pos )
                                                          ctrl.send( ids['fetch-spectrum'],
                                                                     { action: 'spectrum',
                                                                       value: { chan: _chan, index: isource._current_pos } },
                                                                     _update_spectrum, true )
                                                  }
                                              }''',
                     'contour-maskmod': '''   function maskmod_region_clear( ) {
                                                  annotations[0].xs = [ ]
                                                  annotations[0].ys = [ ]
                                                  mask_region_ds.data = { xs: [ [[[]]] ], ys: [ [[[]]] ] }
                                                  mask_region_button.icon = mask_region_icons['off']
                                              }
                                              function maskmod_region_set( region, xs=[ ], ys=[ ] ) {
                                                  if ( xs.length > 0 && ys.length > 0 ) {
                                                      annotations[0].xs = xs
                                                      annotations[0].ys = ys
                                                      mask_region_ds.data = { xs: [ [[[]]] ], ys: [ [[[]]] ] }
                                                      mask_region_button.icon = mask_region_icons['off']
                                                  } else if ( ! casalib.is_empty(contour_ds.data.xs) &&
                                                              ! casalib.is_empty(contour_ds.data.ys) ) {
                                                      annotations[0].xs = [ ]
                                                      annotations[0].ys = [ ]
                                                      mask_region_ds.data = contour_ds.data
                                                      mask_region_ds._src_chan = source.cur_chan
                                                      mask_region_button.icon = mask_region_icons['on']
                                                  } else {
                                                      if ( status ) status.text = '<p>no region found</p>'
                                                      return
                                                  }
                                                  region.fill_color = 'rgba(0, 0, 0, 0)'
                                                  region.line_width = 3
                                                  region.line_dash = 'dashed'
                                                  region.line_color = selector.color
                                              }''',
                     'slider_w_stats':  '''if ( casalib.hotkeys.getScope( ) !== 'channel' ) {
                                               isource.channel( slider.value, isource.cur_chan[0],
                                                               msg => { if ( 'stats' in msg ) { isource.update_statistics( msg.stats ) }
                                                                        if ( 'hist' in msg ) {
                                                                            %s
                                                                            %s
                                                                        }
                                                                        if ( cb ) cb.execute( this ) } )
                                               if ( isource._current_pos )
                                                   update_spectrum( [isource.cur_chan[0], slider.value], isource._current_pos,
                                                                    ( spec ) => {
                                                                        refresh_pixel_display( spec.index,
                                                                                               spec.spectrum.y[spec.chan[1]],
                                                                                               'mask' in spec && spec.mask[spec.chan[1]],
                                                                                               pix_wrld && pix_wrld.label == 'pixel' ? false : true )
                                                                } )
                                               if ( go_to && ! go_to._has_focus ) {
                                                   go_to.value = String( slider.value )
                                               }
                                           }''' % ( span_update( 'span1', 'span2' ), span_update( 'span2', 'span1' ) ),
                     'slider_wo_stats': '''if ( casalib.hotkeys.getScope( ) !== 'channel' ) {
                                               source.channel( slider.value, source.cur_chan[0],
                                                               msg => { if ( 'hist' in msg ) {
                                                                            %s
                                                                            %s
                                                                        }
                                                                        if ( cb ) cb.execute( this ) } )
                                           }''' % ( span_update( 'span1', 'span2' ), span_update( 'span2', 'span1' ) ),
                     ### initialize mask state
                     ###
                     ### mask breadcrumbs
                     ###
                     'mask-state-init': self._js_mode_code['no-bitmask-init'],
                     ###
                     ### code to update stokes after stokes selection from dropdown
                     ###
                     'stokes-change': '''if ( cb_obj.item != stokes.label ) {
                                             source.channel( source.cur_chan[1], %s,
                                                             msg => { stokes.label = cb_obj.item
                                                                      if ( goto_stokes ) { goto_stokes.label = `${cb_obj.item} Channel` }
                                                                      if ( 'stats' in msg ) { source.update_statistics( msg.stats ) }
                                                             } )
                                         }''',
                     ### function to return mask state for current channel, the 'source' (image_data_source) object
                     ### is parameterized so that this can be used in callbacks where 'cb_obj' is set by Bokeh to
                     ### point to our 'source' object
                     'func-curmasks': lambda source="source": '''
                                           function register_mask_change( code ) {
                                               source._mask_breadcrumbs += code
                                           }
                                           function curmasks( cur=source.cur_chan ) { return source._chanmasks[cur[0]][cur[1]] }
                                           function collect_channel_selection( cur=source.cur_chan ) {
                                               if ( typeof(cur) == 'number' ) {
                                                   cur = [ source.cur_chan[0], cur ]    // accept just channel (with stokes implied)
                                               }
                                               const cm = curmasks( cur )
                                               var details = [ ]
                                               var polys = new Set( )
                                               cm[3].forEach( s => {
                                                   details.push( { p: cm[1][s], d: [ ].slice.call(cm[2][s]) } )
                                                   polys.add( cm[1][s] )
                                               } )
                                               return polys.size == 0 ? { masks: [ ], polys: [ ] } :
                                                                        { masks: [ [ [ ].slice.call(cur), details ] ],
                                                                          polys: Array.from(polys).reduce( (acc,p) => {
                                                                              acc.push([ p, (({ type, geometry }) => ({ type, geometry }))(source._polys[p]) ])
                                                                              //            ^^^^^^^^^^^filter^type^and^geometry^^^^^^^^^^^
                                                                              return acc
                                                                          }, [ ] ) }
                                           }
                                           function collect_masks( ) {
                                               var polys = new Set( )
                                               var details = [ ]
                                               for ( let stokes=0; stokes < source._chanmasks.length; ++stokes ) {
                                                   for ( let chan=0; chan < source._chanmasks[stokes].length; ++chan ) {
                                                       if ( source._chanmasks[stokes][chan][0].length == 0 ) continue
                                                       let cur_chan_details = [ ]
                                                       for ( var poly=0; poly < source._chanmasks[stokes][chan][1].length; ++poly ) {
                                                           cur_chan_details.push( { p: source._chanmasks[stokes][chan][1][poly],
                                                                                    d: [ ].slice.call(source._chanmasks[stokes][chan][2][poly]) } )
                                                           polys.add( source._chanmasks[stokes][chan][1][poly] )
                                                       }
                                                       details.push( [[stokes,chan],cur_chan_details] )
                                                   }
                                               }
                                               var poly_result = [ ]
                                               polys.forEach( p => {
                                                   poly_result.push( [ p, (({ type, geometry }) => ({ type, geometry }))(source._polys[p]) ] )
                                                   //                     ^^^^^^^^^^^filter^type^and^geometry^^^^^^^^^^^
                                               } )
                                               return { masks: details, polys: poly_result }
                                           }'''.replace('source',source),
                     ### create a new polygon -- create state and establish a correspondence between the polygon and the
                     ###                         annotation that will be used to represent it for this particular channel
                     'func-newpoly':    '''function newpoly( cm ) {
                                               let anno_id = source._annotation_ids.find( v => ! cm[0].includes(v) ) // find id not in use
                                               if ( typeof(anno_id) != 'string') return null                         // is id reasonable
                                               let poly_id = source._polys.length                                    // all polygons created
                                               let poly = { id: poly_id,
                                                            type: null,
                                                            geometry: { } }
                                               let result = [ source._annotations[anno_id], poly ]
                                               source._polys.push(poly)                                              // all polygons created
                                               cm[0].push(anno_id)                                                   // annotations in use by this channel
                                               cm[1].push(poly_id)                                                   // polygons in use by this channel
                                               return result
                                           }''',
                     ### functions for updating the polygon/annotation state in response to key presses
                     ### ------------------------------------------------------------------------------------------
                     ###   state_update_cursor       -- move cursor to specified polygon index
                     ###   state_clear_cursor        -- unset cursor state (e.g. option release or control pressed)
                     ###   state_next_cursor         -- move the cursor to the next (with wrapping) polygon index
                     ###   state_prev_cursor         -- move the cursor to the previous (with wrapping) polygon index
                     ###   state_nonselection_cursor -- move the cursor to another polygon index which is not in the
                     ###                                selection set (avoid always picking the next index with the
                     ###                                expectation that the user will be adding more polygons to the
                     ###                                selection set (and avoiding always going to the one not desired)
                     ###   state_cursor_to_selection -- add the current cursor polygon to the selection set
                     ###   state_clear_selection     -- clear selection set
                     ###   state_initialize_cursor   -- set cursor to its initial value
                     ###   state_translate_selection -- move all polygons in the selection set by an x/y translation
                     ###   state_copy_selection      -- replace copy buffer contents with the contents of the selection set
                     ###   state_paste_selection     -- past the contents of the copy buffer into the current channel
                     ###                                if the polygons in the copy buffer already exist in the current
                     ###                                paste polygons with an x/y translation (to avoid pasting on top)
                     'key-state-funcs': '''function state_update_cursor( index, cm = curmasks( ) ) {
                                               if ( index >= 0 && index < cm[0].length ) {
                                                   source._annotations[cm[0][index]].line_color = source._cursor_color
                                                   source._cursor = index
                                               } else source._cursor = -1
                                           }
                                           function state_clear_cursor( cm = curmasks( ) ) {
                                               if ( source._cursor >= 0 && source._cursor < cm[0].length ) {
                                                   const result = source._cursor
                                                   source._annotations[cm[0][result]].line_color = null
                                                   source._cursor = -1
                                                   return result
                                               } else {
                                                   source._cursor = -1
                                                   return cm[0].length >= 0 ? 0 : -1
                                               }
                                           }
                                           function state_next_cursor( cm = curmasks( ) ) {
                                               const cursor = state_clear_cursor( cm )
                                               if ( cursor >= 0 && cursor + 1 < cm[0].length )
                                                   state_update_cursor( cursor + 1, cm )
                                               else
                                                   state_update_cursor( 0, cm )
                                           }
                                           function state_prev_cursor( cm = curmasks( ) ) {
                                               const cursor = state_clear_cursor( cm )
                                               if ( cursor >= 0 && cursor - 1 >= 0 )
                                                   state_update_cursor( cursor - 1, cm )
                                               else
                                                   state_update_cursor( cm[0].length - 1, cm )
                                           }
                                           function state_nonselection_cursor( cm = curmasks( ) ) {
                                               let tried_indexes = [ ]
                                               while ( tried_indexes.length < cm[0].length ) {
                                                   // just looping through possible indexes results in always going to an
                                                   // early index which is annoying if it is not one of the ones the user
                                                   // is interested in changing...
                                                   const index = Math.floor(Math.random()*cm[0].length)
                                                   if ( ! tried_indexes.includes(index) ) {
                                                       if ( ! cm[3].includes(index) ) {
                                                           return index
                                                       } else {
                                                           tried_indexes.push(index)
                                                       }
                                                   }
                                               }
                                               return source._cursor
                                           }
                                           function state_cursor_to_selection( cm = curmasks( ) ) {
                                               const cursor = state_clear_cursor( cm )
                                               if ( cursor >= 0 && cursor < cm[0].length ) {
                                                   const index = cm[3].indexOf(cursor);
                                                   if ( index > -1 ) {
                                                       const new_cursor = state_nonselection_cursor( cm )                    // find next cursor before removing from selection (to avoid current cursor)
                                                       source._annotations[cm[0][cursor]].fill_color = source._default_color // remove selection background color
                                                       cm[3].splice( index, 1 )                                              // remove cursor that is already in selection buffer
                                                       if ( new_cursor >= 0 )
                                                           state_update_cursor( new_cursor, cm )                             // advance cursor (for adding multiple mask regions)
                                                       else
                                                           state_update_cursor( cursor, cm )                                 // restore the old cursor (because no non-selected cursor is available)
                                                   } else {
                                                       source._annotations[cm[0][cursor]].fill_color = source._cursor_color  // background changes for masks in selection buffer
                                                       cm[3].push(cursor)                                                    // add cursor to selection buffer
                                                       const new_cursor = state_nonselection_cursor( cm )                    // find next cursor after adding to selection (to avoid current cursor)
                                                       if ( new_cursor >= 0 )
                                                           state_update_cursor( new_cursor, cm )                             // advance cursor (for adding multiple mask regions)
                                                       else
                                                           state_update_cursor( cursor, cm )                                 // restore the old cursor (because no non-selected cursor is available)
                                                   }
                                               }
                                           }
                                           function state_clear_selection( cm = curmasks( ) ) {
                                               // reset selection backgrounds
                                               cm[3].forEach( s => source._annotations[cm[0][s]].fill_color = source._default_color )
                                               // clear selection buffer
                                               cm[3].length = 0
                                           }
                                           function state_initialize_cursor( ) {
                                               state_update_cursor( 0, curmasks( ) )
                                           }
                                           function state_remove_mask( cm = curmasks( ) ) {
                                               register_mask_change('D')
                                               const cursor = source._cursor
                                               const index = cm[3].indexOf(cursor);
                                               if ( index > -1 ) {
                                                   cm[3].splice( index, 1 )                                              // remove cursor that is already in selection buffer
                                                   source._annotations[cm[0][cursor]].fill_color = source._default_color // background changes for masks in selection buffer
                                               }
                                               source._annotations[cm[0][cursor]].xs = [ ]                               // reset x coordinates
                                               source._annotations[cm[0][cursor]].ys = [ ]                               // reset y coordinates
                                               source._annotations[cm[0][cursor]].fill_color = source._default_color     // reset background
                                               source._annotations[cm[0][cursor]].line_color = null                      // remove line
                                               cm[0].splice( cursor, 1 )
                                               cm[1].splice( cursor, 1 )
                                               state_initialize_cursor( )
                                           }
                                           function state_translate_selection( dx, dy, cm = curmasks( ) ) {
                                               register_mask_change('T')
                                               const shape = source.image_source.shape
                                               for ( const s of cm[3] ) {
                                                   if ( dx > 0 && (Math.ceil(Math.max( ...source._annotations[cm[0][s]].xs )) + dx) >= shape[0] ) return;
                                                   if ( dy > 0 && (Math.ceil(Math.max( ...source._annotations[cm[0][s]].ys )) + dy) >= shape[1] ) return;
                                                   if ( dx < 0 && (Math.floor(Math.min( ...source._annotations[cm[0][s]].xs )) + dx) <= 0 ) return;
                                                   if ( dy < 0 && (Math.floor(Math.min( ...source._annotations[cm[0][s]].ys )) + dy) <= 0 ) return;
                                               }
                                               cm[3].forEach( s => {
                                                   if ( dx !== 0 ) source._annotations[cm[0][s]].xs = source._annotations[cm[0][s]].xs.map( x => x + dx )
                                                   if ( dy !== 0 ) source._annotations[cm[0][s]].ys = source._annotations[cm[0][s]].ys.map( y => y + dy )
                                                   cm[2][s][0] += dx
                                                   cm[2][s][1] += dy
                                               } )
                                           }
                                           function state_copy_selection( cm = curmasks( ) ) {
                                               source._copy_buffer = [ [ ], [ ].slice.call(source.cur_chan) ]
                                               //    polygons----------^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^----the channel polys were copied from
                                               // loop over selection indexes and add polygon index + translation
                                               cm[3].forEach( idx => { source._copy_buffer[0].push( [ cm[1][idx], [ ].slice.call(cm[2][idx]) ] ) } )
                                           }
                                           function state_paste_selection( cm = curmasks( ) ) {
                                               function paste( c_indexes ) {
                                                   c_indexes.forEach( idx => {
                                                                          // idx[0]     --  index into the master polygon list
                                                                          // idx[1][0]  --  x offset for this polygon
                                                                          // idx[1][1]  --  y offset for this polygon
                                                                          let anno_id = source._annotation_ids.find( v => ! cm[0].includes(v) )
                                                                          if ( typeof(anno_id) == 'string') {          // is id reasonable
                                                                              cm[0].push(anno_id)                      // claim this annotation
                                                                              cm[3].push(cm[1].length)                 // add pasted poly to selected set
                                                                                                                       //     (position in channel poly list)
                                                                              cm[1].push(idx[0])                       // add poly index (index may occur
                                                                                                                       //     more than once)
                                                                              cm[2].push([].slice.call(idx[1]))        // store x/y translation
                                                                              const poly = source._polys[idx[0]]
                                                                              if ( cm[4][0] == source.cur_chan[0] && cm[4][1] == source.cur_chan[1] ) {
                                                                                  const anno = source._annotations[anno_id]
                                                                                  anno.xs = poly.geometry.xs.map( x => x + idx[1][0] )
                                                                                  anno.ys = poly.geometry.ys.map( y => y + idx[1][1] )
                                                                                  anno.fill_color = source._cursor_color   // change fill color for addition
                                                                                                                           //     to selected set (above)
                                                                              }
                                                                          }
                                                                      } )
                                               }
                                               function paste_with_offset( c_indexes ) {
                                                   // find extent of the polygons to be pasted that already exist in this channel
                                                   function calculate_offset( ) {
                                                       function minmax( ) {
                                                           return c_indexes.reduce( (acc,i) => {
                                                                      // i[0]     --  index into the master polygon list
                                                                      // i[1][0]  --  x offset for this polygon
                                                                      // i[1][1]  --  y offset for this polygon
                                                                      const min = [ Math.min(...source._polys[i[0]].geometry.xs) + i[1][0],
                                                                                    Math.min(...source._polys[i[0]].geometry.ys) + i[1][1] ]
                                                                      const max = [ Math.max(...source._polys[i[0]].geometry.xs) + i[1][0],
                                                                                    Math.max(...source._polys[i[0]].geometry.ys) + i[1][1] ]
                                                                      return acc[0] == null ? [ min, max ] :
                                                                             [ [ Math.min( min[0], acc[0][0] ), Math.min( min[1], acc[1][1] ) ],
                                                                             [ Math.max( max[0], acc[1][0] ), Math.max( max[1], acc[1][1] ) ] ]
                                                                  }, [ null, null ] )
                                                       }
                                                       const offset = 35
                                                       const shape = source.image_source.shape
                                                       const [[xmin,ymin],[xmax,ymax]] = minmax( )
                                                       if ( xmax + offset < shape[0] &&
                                                           ymax + offset < shape[1] ) return [ offset, offset ]
                                                       else if ( xmin - offset >= 0 &&
                                                                 ymin - offset >= 0 ) return [ -offset, -offset ]
                                                       else if ( xmin - offset >= 0 &&
                                                                 ymax + offset < shape[1] ) return [ -offset, offset ]
                                                       else if ( xmax + offset < shape[0] &&
                                                                 ymin - offset >= 0 ) return [ offset, -offset ]
                                                       else if ( xmax + offset < shape[0] ) return [ offset, 0 ]
                                                       else if ( xmin - offset >= 0 ) return [ -offset, 0 ]
                                                       else if ( ymax + offset < shape[1] ) return [ 0, offset ]
                                                       else if ( ymin - offset >= 0 ) return [ 0, -offset ]
                                                       else return [ 0, 0 ]
                                                   }
                                                   if ( c_indexes.length > 0 ) {
                                                       const off = calculate_offset( )
                                                       paste( c_indexes.map( e => [ e[0], [e[1][0]+off[0],e[1][1]+off[1]] ] ) )
                                                   }
                                               }
                                               function groupby( source, predicate ) {
                                                   return source.reduce( (acc,elem) => {
                                                       if ( predicate(elem) ) acc[0].push(elem)
                                                       else acc[1].push(elem)
                                                       return acc }, [ [], [] ] )
                                               }
                                               function poly_already_exists( c_index ) {
                                                   const c_geom = source._polys[c_index[0]].geometry
                                                   const c_delta = c_index[1]
                                                   const potential_matching_chan_polys = cm[1].reduce( (acc,i,cm_index) => {
                                                       // first element of return is the index into the master list of polygons
                                                       // the second is the index into the curmask masks
                                                       if ( source._polys[i].geometry.xs.length == c_geom.xs.length ) acc.push([i,cm_index])
                                                       return acc
                                                   }, [ ] )
                                                   return potential_matching_chan_polys.reduce( (acc,p) => {
                                                       const match_delta = cm[2][p[1]]
                                                       if ( c_geom.xs.every( (element, i) => element === source._polys[p[0]].geometry.xs[i] ) &&
                                                            c_geom.ys.every( (element, i) => element === source._polys[p[0]].geometry.ys[i] ) &&
                                                            c_delta[0] == match_delta[0] && c_delta[1] == match_delta[1] )
                                                           acc.push(p)
                                                       return acc}, [ ] ).length > 0
                                               }
                                               const addition = groupby( source._copy_buffer[0], poly_already_exists )
                                               paste_with_offset( addition[0] )
                                               paste( addition[1] )
                                           }''',
                     ### add a polygon after one is drawn by the user via the Bokeh annotation tools
                     'add-polygon':     '''const cur_masks = curmasks( )
                                           const prev_masks = curmasks(cb_obj._cur_chan_prev)
                                           prev_masks[0].forEach( (i) => {                                  // RESET ANNOTATIONS FROM OLD CHANNEL
                                               cb_obj._annotations[i].xs = [ ];                             // clear Xs for annotations used by prev
                                               cb_obj._annotations[i].ys = [ ]                              // clear Ys for annotations used by prev
                                               cb_obj._annotations[i].line_color = null                     // clear line color
                                               cb_obj._annotations[i].fill_color = cb_obj._default_color    // set default mask fill
                                           } )
                                           cur_masks[2].forEach( ( xlate, i ) => {                          // SET ANNOTATIONS FOR NEW CHANNEL
                                               const mask_annotation = cb_obj._annotations[cur_masks[0][i]] // current annotation
                                               const mask_poly = cb_obj._polys[cur_masks[1][i]]             // current poly
                                               if ( mask_poly ) {                                           // sometimes this is undefined when
                                                                                                            //    releasing the option key
                                                   // set Xs for the current annotation add any X translation from current poly
                                                   mask_annotation.xs = mask_poly.geometry.xs.reduce( (acc,x) => { acc.push(x + xlate[0]); return acc } , [ ] )
                                                   // set Ys for the current annotation add any Y translation from current poly
                                                   mask_annotation.ys = mask_poly.geometry.ys.reduce(
                                                                            (acc,y) => { acc.push(y + xlate[1]); return acc } , [ ] )
                                                                            // restore selections for this channel
                                                                            if ( cur_masks[3].includes( i ) ) mask_annotation.fill_color = cb_obj._cursor_color
                                               } } )
                                               cb_obj._cur_chan_prev = cb_obj.cur_chan''',
                     ### invoke key state management functions in response to keyboard events in the document. this
                     ### code manages the permitted key combinations while most of the state management is handled
                     ### by the state management functions.
                     'setup-key-mgmt':  '''if ( typeof(document._hotkeys_initialized) === 'undefined' ) {
                                               document._hotkeys_initialized = true
                                               //****************************************************
                                               //*** NEED TO IMPLEMENT STOKES TRAVERSAL WITH      ***
                                               //*** Alt+Shift+Up and Alt+Shift+Down when an      ***
                                               //*** image with multiple stokes axes is available ***
                                               //****************************************************

                                               // next channel -- all modes
                                               casalib.hotkeys( 'alt+up,ctrl+up,command+up', {scope: 'channel'},
                                                                (e) => { e.preventDefault( )
                                                                         if ( source.cur_chan[1] + 1 >= source.num_chans[1] ) {
                                                                             // wrap round to the first channel
                                                                             source.channel( 0, source.cur_chan[0] )
                                                                             if ( chan_slider ) { chan_slider.value = 0 }
                                                                         } else {
                                                                             // advance to the next channel
                                                                             source.channel( source.cur_chan[1] + 1, source.cur_chan[0] )
                                                                             if ( chan_slider ) { chan_slider.value = source.cur_chan[1] + 1 }
                                                                         } } )
                                               // previous channel -- all modes
                                               casalib.hotkeys( 'alt+down,ctrl+down,command+down', { scope: 'channel'},
                                                                (e) => { e.preventDefault( )
                                                                         if ( source.cur_chan[1] - 1 >= 0 ) {
                                                                             // advance to the prev channel
                                                                             source.channel( source.cur_chan[1] - 1, source.cur_chan[0] )
                                                                             if ( chan_slider ) { chan_slider.value = source.cur_chan[1] - 1 }
                                                                         } else {
                                                                             // wrap round to the last channel
                                                                             source.channel( source.num_chans[1] - 1, source.cur_chan[0] )
                                                                             if ( chan_slider ) { chan_slider.value = source.num_chans[1] - 1 }
                                                                         } } )

                                               // next polarization/stokes -- all modes
                                               casalib.hotkeys( 'alt+right,ctrl+right,command+right', {scope: 'channel'},
                                                                (e) => { e.preventDefault( )
                                                                         if ( source.cur_chan[0] + 1 >= source.num_chans[0] ) {
                                                                             // wrap round to the first channel
                                                                             source.channel( source.cur_chan[1], 0 )
                                                                         } else {
                                                                             // advance to the next channel
                                                                             source.channel( source.cur_chan[1], source.cur_chan[0] + 1 )
                                                                         } } )
                                               // previous polarization/stokes -- all modes
                                               casalib.hotkeys( 'alt+left,ctrl+left,command+left', { scope: 'channel'},
                                                                (e) => { e.preventDefault( )
                                                                         if ( source.cur_chan[0] - 1 >= 0 ) {
                                                                             // advance to the prev channel
                                                                             source.channel( source.cur_chan[1], source.cur_chan[0] - 1 )
                                                                         } else {
                                                                             // wrap round to the last channel
                                                                             source.channel( source.cur_chan[1], source.num_chans[0] - 1)
                                                                         } } )
                                               %s

                                           }''' % (  self._js_mode_code['no-bitmask-hotkey-setup'] if self._mask_path is None else
                                                     self._js_mode_code['bitmask-hotkey-setup-add-sub'] + self._js_mode_code['bitmask-hotkey-setup'] )
                        }

    def __stop( self ):
        '''stop interactive masking
        '''
        if self._stop_serving_function:
            self._stop_serving_function( )

    def _init_pipes( self ):
        '''set up websockets
        '''
        if self._pipe['image'] is None:
            #######################################################################################################################
            ### init_script code sets up Ctrl key handling for switching the add/subtract plot tool actions from single channel ###
            ### operation to all channel operation                                                                              ###
            #######################################################################################################################
            ### It could be that 'casalib.is_empty' should move to the actual casalib instead of being wedged in here           ###
            #######################################################################################################################
            self._pipe['image'] = ImagePipe( image=self._image_path, mask=self._mask_path,
                                             stats=True, abort=self.__abort, address=find_ws_address( ),
                                             init_script=CustomJS( args=self._mask_add_sub,
                                                                   code='''add._mode = 'chan'
                                                                           sub._mode = 'chan'
                                                                           function is_empty( array ) {
                                                                               return Array.isArray(array) && (array.length == 0 || array.every(is_empty))
                                                                           }
                                                                           casalib.is_empty = is_empty
                                                                           function cube_on( ) {
                                                                               add._mode = 'cube'
                                                                               add.icon = img['add']['cube']
                                                                               sub._mode = 'cube'
                                                                               sub.icon = img['sub']['cube']
                                                                           }
                                                                           function cube_off( ) {
                                                                               add._mode = 'chan'
                                                                               add.icon = img['add']['chan']
                                                                               sub._mode = 'chan'
                                                                               sub.icon = img['sub']['chan']
                                                                           }
                                                                           casalib.hotkeys( '*',
                                                                                            { keyup: true, scope: 'all' },
                                                                                            (e) => {
                                                                                                if ( e.key == "Shift" ) {
                                                                                                    if ( e.type == 'keyup' )
                                                                                                        cube_off( )
                                                                                                    else
                                                                                                        cube_on( )
                                                                                                } } )
                                                                           casalib.hotkeys( '*',
                                                                                            { keyup: true, scope: 'channel' },
                                                                                            (e) => {
                                                                                                if ( e.key == "Shift" ) {
                                                                                                    if ( e.type == 'keyup' )
                                                                                                        cube_off( )
                                                                                                    else
                                                                                                        cube_on( )
                                                                                                } } )''' ) )
        if self._pipe['control'] is None:
            ### self._pipe['control']._freeze_cursor_update is used to keep track of whether pixel
            ### update has been "frozen" (by typing 'f')... for "specmode='mfs'" _freeze_cursor_update
            ### was undefined which resulted in failure to update pixel tracking... so it is now
            ### initialized upon construction in JavaScript...
            self._pipe['control'] = DataPipe( address=find_ws_address( ), abort=self.__abort,
                                              init_script=CustomJS( code='''cb_obj._freeze_cursor_update = false''' ) )

    def path( self ):
        '''return path to CASA image
        '''
        return self._image_papth

    def shape( self ):
        '''return shape of image cube
        '''
        self._init_pipes( )
        return self._pipe['image'].shape

    def channel( self, pixel_type=np.float64 ):
        '''return array for the current channel
        '''
        self._init_pipes( )
        return self._pipe['image'].channel( self._image_source.cur_chan, pixel_type )

    def jsmask_to_raw( self, jsmask ):
        '''The CubeMask raw format uses tuples for dictionary keys but tuples are not a type that can be
        created in javascript...
        '''
        def convert_elem( vec, f=lambda x: x ):
            return { f(chan_or_poly[0]): chan_or_poly[1] for chan_or_poly in vec }
        return { 'masks': convert_elem(jsmask['masks'],tuple), 'polys': convert_elem(jsmask['polys']) }

    def mask( self ):
        return self._mask_path

    def mask_id( self ):
        if self._mask_id is None:
            self._mask_id = str(uuid4( ))
        return self._mask_id

    def set_mask_name( self, new_mask_path ):
        self._mask_path = new_mask_path
        self._pipe['image'].set_mask_name( new_mask_path )

    def set_all_mask_pixels( self, value ):
        '''Set all pixels to the specified boolean value.
        '''
        shape = self._pipe['image'].shape
        for stokes in range(shape[2]):
            for chan in range(shape[3]):
                mask = self._pipe['image'].mask( [stokes,chan], True )
                mask[:] = 1.0 if value else 0.0
                self._pipe['image'].put_mask( [stokes,chan], mask )

    def image( self, maxanno=50, **kw ):
        '''Create the 2D raster display which displays image planes. This widget is should be
        created for all ``cube_mask`` objects because this is the GUI component that ties
        all of the other GUIs together.

        Parameters
        ----------
        maxanno: int
            maximum number of masks that can be drawn in each image channel
        kw: keyword and value
            extra keyword/value paramaters passed on to ``figure``
        '''
        if self._image is None:
            async def receive_return_value( msg, self=self ):
                self._result = self.jsmask_to_raw( msg['value'] )
                self.__stop( )
                return dict( result='stopped', update={ } )

            self._init_pipes( )

            if self._mask_path is None:
                ### multiple annotations are drawn per channel to create mask from scratch
                self._annotations = [ PolyAnnotation( xs=[], ys=[], fill_alpha=0.3, line_color=None, fill_color='black', visible=True ) for _ in range(maxanno) ]
            else:
                ### a bitmask cube is available and a single annotation is used to add or subtract from the bitmask cube
                async def mod_mask( msg, self=self ):
                    err = None
                    shape = self._pipe['image'].shape
                    if msg['action'] == 'addition' or msg['action'] == 'subtract':
                        if 'xs' in msg['value'] and 'ys' in msg['value']:
                            indices = tuple(np.array(list(polygon_indexes( msg['value']['xs'], msg['value']['ys'], shape[:2] ))).T)
                            if len(indices) == 0 and len(msg['value']['xs']) > 0 and len(msg['value']['xs']) == len(msg['value']['ys']):
                                ### this can happen if the entire region is within a single pixel
                                xs = set(map(int,msg['value']['xs']))
                                ys = set(map(int,msg['value']['ys']))
                                if len(xs) == len(ys) and len(xs) == 1:
                                    indices = ( np.array([xs.pop()]), np.array([ys.pop( )]) )
                            if msg['scope'] == 'chan':
                                ### modifying single channel with mouse selected region
                                mask = self._pipe['image'].mask( msg['value']['chan'], True )
                                mask[indices] = 0 if msg['action'] == 'subtract' else 1
                                self._pipe['image'].put_mask( msg['value']['chan'], mask )
                                self._mask_id = str(uuid4( ))                   ### new mask identifier
                                return dict( result='success', update={ } )
                            elif msg['scope'] == 'cube':
                                ### modifying all channels with mouse selected region
                                stokes = msg['value']['chan'][0]
                                for c in range(shape[3]):
                                    mask = self._pipe['image'].mask( [stokes,c], True )
                                    mask[indices] = 0 if msg['action'] == 'subtract' else 1
                                    self._pipe['image'].put_mask( [stokes,c], mask )
                                self._mask_id = str(uuid4( ))                   ### new mask identifier
                                return dict( result='success', update={ } )
                        elif 'src' in msg['value']:
                            if msg['scope'] == 'chan':
                                ### modifying single channel with mask from another channel
                                update={ }
                                if msg['value']['chan'] == msg['value']['src']:
                                    if msg['action'] == 'subtract':
                                        mask = self._pipe['image'].mask( msg['value']['chan'], True )
                                        mask[:,:] = False
                                        self._pipe['image'].put_mask( msg['value']['chan'], mask )
                                        update['clear_region'] = True
                                else:
                                    modifier = self._pipe['image'].mask( msg['value']['src'], True )
                                    mask = self._pipe['image'].mask( msg['value']['chan'], True )
                                    if msg['action'] == 'addition':
                                        mask = np.logical_or( mask, modifier )
                                        self._pipe['image'].put_mask( msg['value']['chan'], mask )
                                    else:
                                        mask = np.logical_and( mask, np.logical_not(modifier) )
                                        self._pipe['image'].put_mask( msg['value']['chan'], mask )

                                self._mask_id = str(uuid4( ))                   ### new mask identifier
                                return dict( result='success', update=update )

                            elif msg['scope'] == 'cube':
                                ### modifying all channels with mask from another channel
                                modifier_index = msg['value']['src']
                                modifier = self._pipe['image'].mask( modifier_index, True )
                                stokes = msg['value']['chan'][0]
                                if msg['action'] == 'addition':
                                    ### addition
                                    for c in range(shape[3]):
                                        ### do not add/subtract the modifier mask with itself
                                        if stokes != modifier_index[0] or c != modifier_index[1]:
                                            mask = self._pipe['image'].mask( [stokes,c], True )
                                            mask = np.logical_or( mask, modifier )
                                            self._pipe['image'].put_mask( [stokes,c], mask )
                                else:
                                    ### subtraction
                                    for c in range(shape[3]):
                                        ### do not add/subtract the modifier mask with itself
                                        if stokes != modifier_index[0] or c != modifier_index[1]:
                                            mask = self._pipe['image'].mask( [stokes,c], True )
                                            mask = np.logical_and( mask, np.logical_not(modifier) )
                                            self._pipe['image'].put_mask( [stokes,c], mask )
                                self._mask_id = str(uuid4( ))                   ### new mask identifier
                                return dict( result='success', update={ } )
                            else:
                                err = "internal error: bad add/subtract scope"
                        else:
                            err = "internal error: bad add/subtract message"
                    elif msg['action'] == 'not':
                        notf = np.vectorize(lambda x: 0.0 if x != 0 else 1.0)
                        if msg['scope'] == 'chan':
                            ### invert single channel
                            ### ctrl.send( ids['mask-mod'], { scope: 'chan', action: 'not',
                            ###                               value: { chan: source.cur_chan } },
                            ###            mask_mod_result )
                            mask = self._pipe['image'].mask( msg['value']['chan'], True )
                            self._pipe['image'].put_mask( msg['value']['chan'], notf(mask) )
                            self._mask_id = str(uuid4( ))                   ### new mask identifier
                            return dict( result='success', update={ } )
                        elif msg['scope'] == 'cube':
                            ### invert all channels
                            ### ctrl.send( ids['mask-mod'], { scope: 'cube', action: 'not',
                            ###                               value: { chan: source.cur_chan } },
                            ###            mask_mod_result )
                            stokes = msg['value']['chan'][0]
                            for c in range(shape[3]):
                                mask = self._pipe['image'].mask( [stokes,c], True )
                                self._pipe['image'].put_mask( [stokes,c], notf(mask) )
                            self._mask_id = str(uuid4( ))                   ### new mask identifier
                            return dict( result='success', update={ } )
                        else:
                            err = "internal error: bad invert scope"
                    else:
                        err = "internal error: bad message action"

                    return dict( result='failure', update={ }, error=err )

                self._annotations = [ PolyAnnotation( xs=[], ys=[], fill_alpha=1.0, line_color=None, fill_color='black', visible=True ) ]
                self._pipe['control'].register( self._ids['mask-mod'], mod_mask )


            self._pipe['control'].register( self._ids['done'], receive_return_value )
            self._image_source = ImageDataSource( image_source=self._pipe['image'] )
            ### fetch stokes labels for all stokes drop
            self._stokes_labels = self._image_source.stokes_labels( )

            self._image = set_attributes( figure( height=self._pipe['image'].shape[1], width=self._pipe['image'].shape[0],
                                                  output_backend="webgl", match_aspect=True,
                                                  tools=[ 'lasso_select', 'box_select',
                                                          'pan', 'wheel_zoom', 'save',
                                                          'reset', 'poly_select',
                                                          self._mask_add_sub['add'],
                                                          self._mask_add_sub['sub'],
                                                          self._mask_add_sub['mask'] ],
                                                  tooltips=None ), **kw )

            ###
            ### set tools that are active by default
            ###
            self._image.toolbar.active_scroll = self._image.select_one(WheelZoomTool)
            self._image.toolbar.active_drag = self._image.select_one(PanTool)
            self._image.toolbar.active_tap = self._image.select_one(PolySelectTool)

            ###
            ### set tick formatting
            ###
            self._image.xaxis.formatter = WcsTicks( axis="x", image_source=self._image_source )
            self._image.yaxis.formatter = WcsTicks( axis="y", image_source=self._image_source )
            self._image.xaxis.major_label_orientation = math.pi/8

            self._image.x_range.range_padding = self._image.y_range.range_padding = 0

            shape = self._pipe['image'].shape
            self._chan_image = self._image.image( image="img", x=0, y=0,
                               dw=shape[0], dh=shape[1],
                               palette=default_palette( True ), level="image",
                               source=self._image_source )
            if self._mask_path is not None and path.isdir(self._mask_path):
                ##
                ## LinearColorMapper must be used because otherwise a bitmask that is
                ## all true or all false is colored with self._color by default because
                ## the "image" range drops to a single value, i.e. the maximum value
                ##
                self._bitmask = self._image.image( image='msk', x=0, y=0, dw=shape[0], dh=shape[1],
                                                   color_mapper=LinearColorMapper( low=0, high=1,
                                                                                   palette=['rgba(0, 0, 0, 0)',self._color] ),
                                                   alpha=0.6, source=self._image_source )
                self._bitmask.visible = False
                ###
                ### _bitmask_contour is the contour that is drawn to show the
                ### mask/non-masked boundary of one channel
                ###
                self._bitmask_contour_ds = self._image_source.mask_contour_source( data={ "xs": [ [[[]]] ], "ys": [ [[[]]] ] } )
                self._bitmask_contour = self._image.multi_polygons( xs="xs", ys="ys", fill_color=None, line_color=self._color,
                                                                    source=self._bitmask_contour_ds )
                self._bitmask_contour.visible = True

                ###
                ### _bitmask_contour_maskmod is the contour that is drawn to represent
                ### the mask/non-masked boundary of one channel for the purpose of
                ### adding or subtracting it from another channel or cube stokes plane
                ###
                self._bitmask_contour_maskmod_ds = ColumnDataSource( data={ "xs": [ [[[]]] ], "ys": [ [[[]]] ] } )
                self._bitmask_contour_maskmod = self._image.multi_polygons( xs="xs", ys="ys", line_width = 3, fill_color=None, line_alpha=0.3,
                                                                            line_color=self._color, line_dash = 'dashed', fill_alpha=0.3,
                                                                            source=self._bitmask_contour_maskmod_ds )
                self._bitmask_contour_maskmod.visible = True


            if self._pipe['image'].have_mask0( ):
                self._mask0 = self._image.image( image='msk0', x=0, y=0, dw=shape[0], dh=shape[1],
                                                 color_mapper=LinearColorMapper( low=0, high=1,
                                                                                 palette=['#000000','rgba(0, 0, 0, 0)'] ),
                                                 source=self._image_source )

            self._image.grid.grid_line_width = 0.5

            for annotation in self._annotations:
                self._image.add_layout(annotation)

        return self._image

    def goto( self, **kw ):
        if self._goto is None:
            self._init_pipes( )
            self._goto_txt = set_attributes( EvTextInput( value=self._slider.start if self._slider else '0',
                                                          stylesheets=[ InlineStyleSheet( css='''.bk-input { border-bottom-left-radius: 0; border-top-left-radius: 0; margin-left: -0.45em; }''' ) ],
                                                          width=85 ), **kw )
            self._goto_stokes = Dropdown( label="I Channel", menu=self._stokes_labels, stylesheets=[ InlineStyleSheet( css='''.bk-btn { background-color: rgb( 230, 230, 230 ); padding: 7px; padding-top: 8px; border-bottom-right-radius: 0; border-top-right-radius: 0; margin-right: -0.45em; }''' ) ], width=80 )
            self._goto = row( self._goto_stokes, self._goto_txt, spacing=-1 )

        return self._goto

    def slider( self, callback=None, **kw ):
        '''Return slider that is used to change the image plane that is
        displayed on the 2D raster display.

        Parameters
        ----------
        kw: keyword and value
            extra keyword/value paramaters passed on to ``Slider``
        '''
        if self._slider is None:
            self._init_pipes( )
            shape = self._pipe['image'].shape
            slider_end = shape[-1]-1
            self._slider = set_attributes( Slider( start=0, end=1 if slider_end == 0 else slider_end , value=0, step=1,
                                                   title="Channel" ), **kw )
            self._slider_callback = callback
            if slider_end == 0:
                # for a cube with one channel, a slider is of no use
                self._slider.disabled = True

        return self._slider

    def tapedeck( self ):
        if self._slider is None:
            raise RuntimeError( "tapedeck can only be created after the slider has been created" )

        stylesheets= [ InlineStyleSheet( css='''.bk-btn { padding-right: 0px; padding-left: 0px; }''' ) ]
        callback=CustomJS( args=dict( slider=self._slider ),
                           code='''if ( cb_obj.name == 'forw' )
                                   if ( cb_obj.name == 'back' ) ''' )
        srt = 0
        end = 3
        fwd = 2
        bck = 1
        self._tapedeck = [ TipButton( icon=svg_icon([ '20px', 'fast-backward']), button_type='light',
                                      tooltip=Tooltip( content=HTML( 'move to first channel' ), position='bottom' ),
                                      stylesheets=stylesheets, name='tofront' ),
                           TipButton( icon=svg_icon([ '20px', 'step-backward']), button_type='light',
                                      tooltip=Tooltip( content=HTML( 'move to previous channel' ), position='bottom' ),
                                      stylesheets=stylesheets, name='back' ),
                           TipButton( icon=svg_icon([ '20px', 'step-forward']), button_type='light',
                                      tooltip=Tooltip( content=HTML( 'move to next channel' ), position='bottom' ),
                                      stylesheets=stylesheets, name='forw' ),
                           TipButton( icon=svg_icon([ '20px', 'fast-forward']), button_type='light',
                                      tooltip=Tooltip( content=HTML( 'move to last channel' ), position='bottom' ),
                                      stylesheets=stylesheets, name='toend' ) ]

        self._tapedeck[fwd].js_on_click( CustomJS( args=dict( slider=self._slider ),
                                                   code='''slider.value = slider.value == slider.end ? slider.start : slider.value + 1''' ) )
        self._tapedeck[bck].js_on_click( CustomJS( args=dict( slider=self._slider ),
                                                   code='''slider.value = slider.value == slider.start ? slider.end : slider.value - 1''' ) )
        self._tapedeck[end].js_on_click( CustomJS( args=dict( slider=self._slider ),
                                                   code='''slider.value = slider.end''' ) )
        self._tapedeck[srt].js_on_click( CustomJS( args=dict( slider=self._slider ),
                                                   code='''slider.value = slider.start''' ) )

        return row( *self._tapedeck )

    def spectrum( self, **kw ):
        '''Return the line graph of spectrum from the image cube which is updated
        in response to moving the cursor within the 2D raster display.

        Parameters
        ----------
        kw: keyword and value
            extra keyword/value paramaters passed on to ``figure``
        '''
        if self._spectrum is None:
            if self._image is None:
                ###
                ### an exception is raised instead of just creating the image display because if we create
                ### it here [by calling self.image( )], the user will silently lose the ability to set the
                ### maximum number of annotations per channel (along with other future parameters)
                ###
                raise RuntimeError('spectrum( ) requires an image cube display, but one has not yet been created')

            nelem = self._pipe['image'].shape[-1]
            self._image_spectrum = ColumnDataSource( data={ 'x': list(range(nelem)), 'y': [0] * nelem } )

            self._sp_span = Span( location=-1,
                                  dimension='height',
                                  line_color='slategray',
                                  line_width=2,
                                  visible=False )

            self._cb['sppos'] = CustomJS( args=dict(span=self._sp_span),
                                          code = """var geometry = cb_data['geometry'];
                                                            var x_pos = Math.round(geometry.x);
                                                            var y_pos = Math.round(geometry.y);
                                                            if ( isFinite(x_pos) && isFinite(y_pos) ) {
                                                                span.visible = true
                                                                span.location = x_pos
                                                            } else {
                                                                span.visible = false
                                                                span.location = -1
                                                            }""" )

            self._hover['spectrum'] = HoverTool( callback=self._cb['sppos'] )

            self._spectrum = set_attributes( figure( height=180, width=800,
                                                    tools=[ self._hover['spectrum'] ] ), **kw )
            self._spectrum.add_layout(self._sp_span)

            self._spectrum.x_range.range_padding = self._spectrum.y_range.range_padding = 0
            self._spectrum.line( x='x', y='y', source=self._image_spectrum )
            self._spectrum.grid.grid_line_width = 0.5

        return self._spectrum

    def coorddesc( self ):
        return self._pipe['image'].coorddesc( )

    def statistics( self, **kw ):
        '''retrieve a DataTable which is updated in response to changes in the
        image cube display
        '''
        if self._statistics is None:
            image_stats = self._pipe['image'].statistics( [0,0] )
            self._statistics_source = ColumnDataSource( { 'labels': list(image_stats.keys( )),
                                                          'values': list(image_stats.values( )) } )

            stats_column = [ TableColumn(field='labels', title='Statistics', width=75),
                             TableColumn(field='values', title='Values') ]

            # using set_attributes allows the user to override defaults like 'width=400'
            self._statistics = set_attributes( DataTable( source=self._statistics_source, columns=stats_column ), **kw )
            #self._statistics = set_attributes( DataTable( source=self._statistics_source, columns=stats_column,
            #                                              height_policy='fit' ), **kw )
                                                          #height_policy='fit' ), **kw )
                                                          #width=400, height=200, height_policy='fit' ), **kw )
                                                          #width=400, height=200, sizing_mode='stretch_height' ), **kw )
                                                          #width=400, height=200, height_policy='max' ), **kw )
                                                          #width=400, height=200, autosize_mode='none', height_policy='max' ), **kw )
                                                          #width=400, height=200, autosize_mode='none', sizing_mode='stretch_height' ), **kw )
                                                          #width=400, height=200, autosize_mode='none' ), **kw )
            if self._mask_path:
                async def config_statistics( msg, self=self ):
                    if 'value' in msg and self._statistics_use_mask != bool(msg['value']):
                        self._statistics_use_mask = bool(msg['value'])
                        self._pipe['image'].statistics_config( use_mask=self._statistics_use_mask )
                        return dict( result='OK', update={ } )
                    else:
                        return dict( result='NOP', update={ } )

                self._pipe['control'].register( self._ids['config-statistics'], config_statistics )
                self._statistics_mask = Dropdown( label="Channel Statistics", button_type='light', margin=(5,0,-1,0),
                                                  menu=[ 'Channel Statistics', 'Mask Statistics' ],
                                                  css_classes=['cg-btn-selector'] )

        if self._mask_path:
            return column( self._statistics_mask,
                           self._statistics )
        else:
            return self._statistics

    def palette( self, **kw ):
        '''retrieve a Select widget which allow for changing the pseudocolor palette
        '''
        if self._palette is None:
            if self._image is None:
                ###
                ### an exception is raised instead of just creating the image display because if we create
                ### it here [by calling self.image( )], the user will silently lose the ability to set the
                ### maximum number of annotations per channel (along with other future parameters)
                ###
                raise RuntimeError('palette( ) requires an image cube display, but one has not yet been created')

            async def fetch_palette( msg, self=self ):
                if 'value' in msg:
                    return dict( result=find_palette(msg['value']), value=msg['value'], update={ } )
                else:
                    return dict( result=None, value=None, update={ } )

            self._pipe['control'].register( self._ids['palette'], fetch_palette )

            self._palette = set_attributes( Dropdown( label=default_palette( ), button_type='light', margin=(-1, 0, 0, 0),
                                                      sizing_mode='scale_height', menu=available_palettes( ) ), **kw )
            self._palette.js_on_click( CustomJS( args=dict( image=self._chan_image,
                                                            ids=self._ids,
                                                            ctrl=self._pipe['control'] ),
                                                 code='''function receive_palette( msg ) {
                                                             if ( 'result' in msg && msg.result != null ) {
                                                                 let cm = image.glyph.color_mapper
                                                                 cm.palette = msg.result
                                                                 cm.change.emit( )
                                                                 cb_obj.origin.label = msg.value
                                                             }
                                                         }
                                                         ctrl.send( ids['palette'],
                                                                    { action: 'palette', value: this.item },
                                                                    receive_palette )''' ) )

        return Tip( self._palette, tooltip=Tooltip( content=HTML("Select the colormap used to render the image cube"), position="right" ) )


    def colormap_adjust( self, **kw ):

        chan = self.channel( )
        bins = np.linspace( chan.min( ), chan.max( ), self._cm_adjust['bins'] )
        hist, edges = np.histogram( chan, density=False, bins=bins )

        span_edited_funcs = '''function set_edited( span ) {
                                   if (typeof span._original_dash == 'undefined')
                                       span._original_dash = span.line_dash
                                   span.line_dash = [ ]
                                   span._edited = true
                               }
                               function clear_edited( span ) {
                                   if (typeof span._original_dash != 'undefined')
                                       span.line_dash = span._original_dash
                                   span._edited = false
                               }
                               '''

        self._cm_adjust['span one'] = EditSpan( location=edges[0], dimension='height', line_color='red', line_width=1,
                                                 editable=True, line_dash='dashed' )
        self._cm_adjust['span two'] = EditSpan( location=edges[-1], dimension='height', line_color='red', line_width=1,
                                                  editable=True, line_dash='dashed' )

        ###
        ### Bokeh supports 'description=Tooltip( content=HTML("..."), position="..." )'. However,
        ### The Tooltip(...) works by creating an "i" in a circle with the label that can be clicked.
        ### With "prefix=..." and no label, no button is displayed.
        ###
        self._cm_adjust['min input'] =  TextInput( value=repr(edges[0]), prefix="min" )
        self._cm_adjust['min input'].js_on_event( ValueSubmit, CustomJS( args=dict( span1=self._cm_adjust['span one'],
                                                                                    span2=self._cm_adjust['span two'] ),
                                                                         code=span_edited_funcs +
                                                                              '''if ( span1.location <= span2.location ) {
                                                                                     span1._refresh_colormap = true
                                                                                     span1.location = Number(cb_obj.origin.value)
                                                                                     set_edited(span1)
                                                                                 } else {
                                                                                     span2._refresh_colormap = true
                                                                                     span2.location = Number(cb_obj.origin.value)
                                                                                     set_edited(span2)
                                                                                 }''' ) )

        self._cm_adjust['max input'] = TextInput( value=repr(edges[-1]), prefix="max" )
        self._cm_adjust['max input'].js_on_event( ValueSubmit, CustomJS( args=dict( span1=self._cm_adjust['span one'],
                                                                                    span2=self._cm_adjust['span two'] ),
                                                                         code=span_edited_funcs +
                                                                              '''if ( span1.location >= span2.location ) {
                                                                                     span1._refresh_colormap = true
                                                                                     span1.location = Number(cb_obj.origin.value)
                                                                                     set_edited(span1)
                                                                                 } else {
                                                                                     span2._refresh_colormap = true
                                                                                     span2.location = Number(cb_obj.origin.value)
                                                                                     set_edited(span2)
                                                                                 }''' ) )

        self._cm_adjust['reset'] = CBResetTool( description="Reset pan/zoom and extents" )
        self._cm_adjust['fig'] = figure( width=250, height=200, toolbar_location='above',
                                         tools=[ self._cm_adjust['reset'],
                                                 'wheel_zoom', 'pan',
                                                 ResetTool( description="Reset pan/zoom but preserve extents" ) ] )

        self._cm_adjust['fig'].toolbar.active_scroll = self._cm_adjust['fig'].select_one(WheelZoomTool)

        # Create a new BasicTickFormatter
        formatter = BasicTickFormatter()

        # Set the number of decimal places to display
        formatter.precision = 1

        self._cm_adjust['fig'].yaxis.formatter = formatter
        self._cm_adjust['fig'].renderers.extend([self._cm_adjust['span one'], self._cm_adjust['span two']])

        self._cm_adjust['hist-ds'] = self._pipe['image'].histogram_source( data=dict( left=list(edges[:-1]), right=list(edges[1:]), top=list(hist), bottom=[0]*len(hist) ) )
        self._cm_adjust['hist-glyph'] = Quad( left="left", right="right", top="top", bottom=0, fill_color="blue", line_color="blue" )
        self._cm_adjust['histogram'] = self._cm_adjust['fig'].add_glyph( self._cm_adjust['hist-ds'], self._cm_adjust['hist-glyph'] )

        ### linear: 𝑦=𝑥
        ### log: 𝑦=log𝛼𝑥+1(𝛼𝑥+1)  == Math.log(alpha * x + 1.0) / Math.log(alpha + 1.0)
        ### square root: 𝑦=√x
        ### square: 𝑦=𝑥^2
        ### gamma: 𝑦=𝑥^𝛾
        ### power: 𝑦=(𝛼^𝑥−1)/(𝛼−1)
        self._cm_adjust['alpha-value'] = TextInput( value="1000", prefix="alpha", max_width=170, visible=False )
        self._cm_adjust['gamma-value'] = TextInput( value="1", prefix="gamma", max_width=170, visible=False )
        self._cm_adjust['equation'] = Div(text='''<math><mrow><mi>y</mi><mo>=</mo><mi>x</mi></mrow></math>''')  # linear
        self._cm_adjust['scaling'] = Dropdown( label='linear',
                                               menu=[ ('linear', 'linear'), ('log', 'log'), ('sqrt','sqrt'),
                                                      ('square', 'square'), ('gamma', 'gamma'), ('power', 'power') ],
                                               button_type='light' )

        colormap_refresh_code = '''let args = { }
                                   if ( alpha.visible ) args = { alpha: parseFloat(alpha.value), ...args }
                                   if ( gamma.visible ) args = { gamma: parseFloat(gamma.value), ...args }
                                   const [ minspan, maxspan ] = span1.location <= span2.location ? [ span1, span2 ] : [ span2, span1 ]
                                   source.adjust_colormap( [ minspan._edited ? [ minspan.location ] : [ ],
                                                             maxspan._edited ? [ maxspan.location ] : [ ] ],
                                                           { scaling: scaling.label, args }, msg => { source.refresh( ) } )'''

        ###
        ###  "( span1._editing && span2._editing )" update happens when the
        ###  one of the spans is being dragged. Image is updated here when
        ###  the LODEnd event is received
        ###
        ###  Otherwise the only time this should be called is in responce to
        ###  either the min or max text input being changed directly. In this
        ###  case the image is updated as a result of the text input change.
        ###
        span_cb = '''if ( span1._editing || span2._editing ) {
                         min.value = (Math.min(span1.location,span2.location)).toString( )
                         max.value = (Math.max(span1.location,span2.location)).toString( )
                     }
                     if ( cb_obj._refresh_colormap ) {
                         cb_obj._refresh_colormap = false
                         %s
                     }'''

        self._cm_adjust['span one'].js_on_change( 'location', CustomJS( args=dict( source=self._image_source,
                                                                                   min=self._cm_adjust['min input'],
                                                                                   max=self._cm_adjust['max input'],
                                                                                   span1=self._cm_adjust['span one'],
                                                                                   span2=self._cm_adjust['span two'],
                                                                                   scaling=self._cm_adjust['scaling'],
                                                                                   alpha=self._cm_adjust['alpha-value'],
                                                                                   gamma=self._cm_adjust['gamma-value'],
                                                                                   equation=self._cm_adjust['equation'] ),
                                                                        code=span_cb % colormap_refresh_code ) )
        self._cm_adjust['span two'].js_on_change( 'location', CustomJS( args=dict( source=self._image_source,
                                                                                   min=self._cm_adjust['min input'],
                                                                                   max=self._cm_adjust['max input'],
                                                                                   span1=self._cm_adjust['span one'],
                                                                                   span2=self._cm_adjust['span two'],
                                                                                   scaling=self._cm_adjust['scaling'],
                                                                                   alpha=self._cm_adjust['alpha-value'],
                                                                                   gamma=self._cm_adjust['gamma-value'],
                                                                                   equation=self._cm_adjust['equation'] ),
                                                                        code=span_cb % colormap_refresh_code ) )

        self._cm_adjust['span one'].js_on_event( LODStart, CustomJS( code= span_edited_funcs +
                                                                           '''cb_obj.origin._editing = true
                                                                              set_edited( cb_obj.origin )''' ) )
        self._cm_adjust['span one'].js_on_event( LODEnd, CustomJS( args=dict( source=self._image_source,
                                                                              min=self._cm_adjust['min input'],
                                                                              max=self._cm_adjust['max input'],
                                                                              span1=self._cm_adjust['span one'],
                                                                              span2=self._cm_adjust['span two'],
                                                                              scaling=self._cm_adjust['scaling'],
                                                                              alpha=self._cm_adjust['alpha-value'],
                                                                              gamma=self._cm_adjust['gamma-value'],
                                                                              equation=self._cm_adjust['equation'] ),
                                                                   code='''cb_obj.origin._editing = false;'''+colormap_refresh_code ) )
        self._cm_adjust['span two'].js_on_event( LODStart, CustomJS( code= span_edited_funcs +
                                                                           '''cb_obj.origin._editing = true
                                                                              set_edited( cb_obj.origin )''' ) )
        self._cm_adjust['span two'].js_on_event( LODEnd, CustomJS( args=dict( source=self._image_source,
                                                                              min=self._cm_adjust['min input'],
                                                                              max=self._cm_adjust['max input'],
                                                                              span1=self._cm_adjust['span one'],
                                                                              span2=self._cm_adjust['span two'],
                                                                              scaling=self._cm_adjust['scaling'],
                                                                              alpha=self._cm_adjust['alpha-value'],
                                                                              gamma=self._cm_adjust['gamma-value'],
                                                                              equation=self._cm_adjust['equation'] ),
                                                                   code='''cb_obj.origin._editing = false;'''+colormap_refresh_code ) )


        update_scaling_state = '''alpha.visible = false
                                  gamma.visible = false
                                  if ( scaling.label == 'linear' ) {
                                      equation.text = '<math><mrow><mi>y</mi><mo>=</mo><mi>x</mi></mrow></math>'
                                  } else if ( scaling.label == 'log' ) {
                                      alpha.visible = true
                                      equation.text = '<math><mrow><mi>y</mi><mo>=</mo><msub><mi>log</mi><mrow><mn>&alpha;</mn><mo>+</mo><mn>1</mn></mrow></msub><mrow><mo>(</mo><mn>&alpha;</mn><mn>x</mn></mrow><mo>+</mo><mn>1</mn><mo>)</mo></mrow></mrow></math>'
                                  } else if ( scaling.label == 'sqrt' ) {
                                      equation.text = '<math><mrow><mi>y</mi><mo>=</mo><msqrt><mi>x</mi></msqrt></mrow></math>'
                                  } else if ( scaling.label == 'square' ) {
                                      equation.text = '<math><mrow><mi>y</mi><mo>=</mo><msup><mi>x</mi><mn>2</mn></msup></mrow></math>'
                                  } else if ( scaling.label == 'gamma' ) {
                                      gamma.visible = true
                                      equation.text = '<math><mrow><mi>y</mi><mo>=</mo><msup><mi>x</mi><mn>&gamma;</mn></msup></mrow></math>'
                                  } else if ( scaling.label == 'power' ) {
                                      alpha.visible = true
                                      equation.text = '<math><mrow><mi>y</mi><mo>=</mo><msub><mi>log</mi><mrow><mn>&alpha;</mn><mo>+</mo><mn>1</mn></mrow></msub><mrow><mo>(</mo><msup><mn>&alpha;</mn><mn>x</mn></msup><mo>+</mo><mn>1</mn><mo>)</mo></mrow></mrow></math>'
                                  } else if ( scaling.label == 'power' ) {
                                      alpha.visible = true
                                      equation.text = '<math><mrow><mi>y</mi><mo>=</mo><mfrac><mrow><msup><mn>&alpha;</mn><mi>x</mi></msup><mo>-</mo><mn>1</mn></mrow><mrow><mn>&alpha;</mn><mo>-</mo><mn>1</mn></mrow></mfrac></mrow></math>'
                                  } else {
                                      equation.text = scaling.label
                                  }'''

        self._cm_adjust['reset'].postcallback = CustomJS( args=dict( span1=self._cm_adjust['span one'],
                                                                     span2=self._cm_adjust['span two'],
                                                                     mintxt=self._cm_adjust['min input'],
                                                                     maxtxt=self._cm_adjust['max input'],
                                                                     source=self._image_source,
                                                                     histogram=self._cm_adjust['histogram'],
                                                                     scaling=self._cm_adjust['scaling'],
                                                                     alpha=self._cm_adjust['alpha-value'],
                                                                     gamma=self._cm_adjust['gamma-value'],
                                                                     equation=self._cm_adjust['equation'] ),
                                                          code=span_edited_funcs +
                                                               '''scaling.label = scaling.menu[0][0]
                                                                  %s
                                                                  scaling.change.emit( )
                                                                  span1.location = histogram.data_source.data.left[0]
                                                                  clear_edited(span1)
                                                                  span2.location = histogram.data_source.data.right[histogram.data_source.data.right.length-1]
                                                                  clear_edited(span2)
                                                                  mintxt.value = span1.location.toString( )
                                                                  maxtxt.value = span2.location.toString( )
                                                                  %s''' % ( update_scaling_state, colormap_refresh_code ) )

        self._cm_adjust['scaling'].js_on_event( "menu_item_click", CustomJS( args=dict( span1=self._cm_adjust['span one'],
                                                                                        span2=self._cm_adjust['span two'],
                                                                                        mintxt=self._cm_adjust['min input'],
                                                                                        maxtxt=self._cm_adjust['max input'],
                                                                                        source=self._image_source,
                                                                                        histogram=self._cm_adjust['histogram'],
                                                                                        scaling=self._cm_adjust['scaling'],
                                                                                        alpha=self._cm_adjust['alpha-value'],
                                                                                        gamma=self._cm_adjust['gamma-value'],
                                                                                        equation=self._cm_adjust['equation'] ),
                                                                             code='''if ( cb_obj.item != cb_obj.origin.label ) {
                                                                                         scaling.label = cb_obj.item
                                                                                         %s
                                                                                         %s
                                                                                     }''' % ( update_scaling_state, colormap_refresh_code )) )

        scaling_parameter_callback = CustomJS( args=dict( span1=self._cm_adjust['span one'],
                                                          span2=self._cm_adjust['span two'],
                                                          mintxt=self._cm_adjust['min input'],
                                                          maxtxt=self._cm_adjust['max input'],
                                                          source=self._image_source,
                                                          histogram=self._cm_adjust['histogram'],
                                                          scaling=self._cm_adjust['scaling'],
                                                          alpha=self._cm_adjust['alpha-value'],
                                                          gamma=self._cm_adjust['gamma-value'],
                                                          equation=self._cm_adjust['equation'] ),
                                               code=colormap_refresh_code )

        self._cm_adjust['alpha-value'].js_on_change( 'value', scaling_parameter_callback )
        self._cm_adjust['gamma-value'].js_on_change( 'value', scaling_parameter_callback )

        async def colormap_adjust_update( msg, self=self ):
            if 'action' in msg and msg['action'] == 'fetch':
                chan = self.channel( )
                bins = np.linspace( chan.min( ), chan.max( ), self._cm_adjust['bins'] )
                hist, edges = np.histogram( chan, density=False, bins=bins )
                return dict( result='success', hist=hist, edges=edges )

            return dict( result='failure', update={ } )

        return column( self._cm_adjust['fig'],
                       row( Tip( self._cm_adjust['min input'],
                                  tooltip=Tooltip( content=HTML("set minimum clip here or drag the left red line above"),
                                                   position="top" ) ),
                            Tip( self._cm_adjust['max input'],
                                  tooltip=Tooltip( content=HTML("set maximum clip here or drag the right red line above"),
                                                   position="top_left" ) ), width_policy='min' ),
                       row( Tip( self._cm_adjust['scaling'],
                                  tooltip=Tooltip( content=HTML('scaling function applied to image intensities'),
                                                   position="top" ) ),
                            self._cm_adjust['equation'] ),
                       row( Tip( self._cm_adjust['alpha-value'],
                                  tooltip=Tooltip( content=HTML('set alpha value as indicated in the equation'),
                                                   position="top" ) ),
                            Tip( self._cm_adjust['gamma-value'],
                                  tooltip=Tooltip( content=HTML('set gamma value as indicated in the equation'),
                                                   position="top" ) ) ) )

    def bitmask_controls( self, **kw ):

        if self._bitmask is None:
            raise RuntimeError('cube bitmask not in use')

        ###
        ### retrieve controls for adjusting the cube bitmask
        ###
        ###    NOTE: the self._bitmask_color_selector change function is setup
        ###          in the "connect" member function
        ###
        self._bitmask_color_selector = ColorPicker( width_policy='fixed', width=40, color=self._color, margin=(-1, 0, 0, 0),
                                                    stylesheets=[ InlineStyleSheet( css='''.bk-input { border: 0px solid #ccc;
                                                                                                       padding: 0 var(--padding-vertical); }''' ) ] )

        mask_alpha_pick = Spinner( width_policy='fixed', width=55, low=0.0, high=1.0, mode='float', step=0.1, value=0.6, margin=(-1, 0, 0, 0), visible=False )
        mask_alpha_pick.js_on_change( 'value', CustomJS( args=dict( bitmask=self._bitmask ),
                                                         code='''let gl = bitmask.glyph
                                                                 gl.global_alpha.value = cb_obj.value
                                                                 gl.change.emit( )''' ) )

        ### setting button background color does not work with Bokeh 2.4.3
        self._bitmask_transparency_button = set_attributes( Dropdown( label='contour', button_type='light', margin=(-1, 0, 0, 0),
                                                                      sizing_mode='scale_height', menu=['contour','masked','unmasked'] ), **kw )
        self._bitmask_transparency_button.js_on_click( CustomJS( args=dict( bitmask=self._bitmask, contour=self._bitmask_contour,
                                                                            contour_ds=self._bitmask_contour_ds,
                                                                            selector=self._bitmask_color_selector,
                                                                            alpha=mask_alpha_pick ),
                                                        code='''let cm = bitmask.glyph.color_mapper
                                                                if ( bitmask._transparent == null ) {
                                                                    bitmask._transparent = cm.palette[0]
                                                                }
                                                                if ( this.item == 'masked' ) {
                                                                    cm.palette[0] = bitmask._transparent
                                                                    cm.palette[1] = selector.color
                                                                    contour.visible = false
                                                                    bitmask.visible = true
                                                                    alpha.visible = true
                                                                    cm.change.emit( )
                                                                } else if ( this.item == 'unmasked' ) {
                                                                    cm.palette[0] = selector.color
                                                                    cm.palette[1] = bitmask._transparent
                                                                    contour.visible = false
                                                                    bitmask.visible = true
                                                                    alpha.visible = true
                                                                    cm.change.emit( )
                                                                } else if ( this.item == 'contour' ) {
                                                                    contour.visible = true
                                                                    bitmask.visible = false
                                                                    alpha.visible = false
                                                                }
                                                                this.origin.label = this.item''' ) )

        return ( Tip( self._bitmask_color_selector,
                      tooltip=Tooltip( content=HTML("Set the color used for drawing the mask"), position="right" ) ),
                 Tip( mask_alpha_pick,
                      tooltip=Tooltip( content=HTML("<b>If</b> the mask is indicated with shading, this sets the opaqueness of the shading"),
                                       position="bottom" ) ),
                 Tip( self._bitmask_transparency_button,
                      tooltip=Tooltip( content=HTML("The mask can be displayed as a <b>contour</b> or the <b>masked/unmasked</b> portion can be shaded"),
                                       position='right' ) ) )


    def channel_ctrl( self ):
        '''Return a text label for the current channel being displayed.
        It will be updated as the channel or stokes axis changes.
        '''
        if self._image is None:
            raise RuntimeError('cube image not in use')
        self._channel_ctrl = PreText( text='Channel 0', min_width=100 )
        self._channel_ctrl_stokes_dropdown = Dropdown( label='I', button_type='light', margin=(-1, 0, 0, 0), sizing_mode='scale_height', width=25 )
        self._channel_ctrl_group = ( self._channel_ctrl,
                                     Tip( self._channel_ctrl_stokes_dropdown,
                                          tooltip=Tooltip( content=HTML('Select which of the <b>image</b> or <b>stokes</b> planes to display'),
                                                           position='right' ) ) )
        return self._channel_ctrl_group

    def coord_ctrl( self ):
        '''Return a text label for the current channel being displayed.
        It will be updated as the channel or stokes axis changes.
        '''
        if self._image is None:
            raise RuntimeError('cube image not in use')
        self._coord_ctrl_dropdown = Dropdown( label='world', button_type='light', margin=(-1, 0, 0, 0),
                                              sizing_mode='scale_height', menu=['pixel','world'] )
        self._coord_ctrl_dropdown.js_on_click( CustomJS( args=dict( source=self._image_source,
                                                                    xaxis=self._image.xaxis.formatter,
                                                                    yaxis=self._image.yaxis.formatter ),
                                                                    code='''xaxis.coordinates(this.item)
                                                                            yaxis.coordinates(this.item)
                                                                            source.signal_change( )
                                                                            this.origin.label = this.item''' ) )

        self._coord_ctrl_group = Tip( self._coord_ctrl_dropdown,
                                      tooltip=Tooltip( content=HTML("Axes can be labeled in <b>pixel</b> or <b>world</b> coordinates"),
                                                       position="right" ) )

        return self._coord_ctrl_group

    def status_text( self, text='', **kw ):
        self._status_div =  set_attributes( Div( text=text ), **kw )
        return self._status_div

    def pixel_tracking_text( self ):

        self._pixel_tracking_text = Div( text='', min_width=200 )

        async def fetch_spectrum( msg, self=self ):
            if msg['action'] == 'spectrum':
                chan = msg['value']['chan']
                index = msg['value']['index']
                spectrum, mask = self._pipe['image'].spectrum( index + [chan[0]], True )
                return dict( result='success', update=dict( spectrum=spectrum,
                                                            mask=mask,
                                                            index=index, chan=chan ) )

        self._pipe['control'].register( self._ids['fetch-spectrum'], fetch_spectrum )
        return self._pixel_tracking_text

    def connect( self ):
        '''Connect the callbacks which are used by the masking GUIs that
        have been created.
        '''

        self._mask_add_sub['add'].callback = CustomJS( args=dict( annotations=self._annotations,
                                                                  source=self._image_source,
                                                                  ctrl=self._pipe['control'],
                                                                  ids=self._ids,
                                                                  stats_source=self._statistics_source,
                                                                  mask_region_icons=self._mask_icons_,
                                                                  mask_region_button=self._mask_add_sub['mask'],
                                                                  mask_region_ds=self._bitmask_contour_maskmod_ds,
                                                                  contour_ds=self._bitmask_contour_ds,
                                                                  status=self._status_div ),
                                                       code=self._js['contour-maskmod'] + self._js_mode_code['bitmask-hotkey-setup-add-sub'] +
                                                            '''if ( cb_obj._mode == 'cube' ) mask_add_cube( )
                                                               else mask_add_chan( )''' )
        self._mask_add_sub['sub'].callback = CustomJS( args=dict( annotations=self._annotations,
                                                                  source=self._image_source,
                                                                  ctrl=self._pipe['control'],
                                                                  ids=self._ids,
                                                                  stats_source=self._statistics_source,
                                                                  mask_region_icons=self._mask_icons_,
                                                                  mask_region_button=self._mask_add_sub['mask'],
                                                                  mask_region_ds=self._bitmask_contour_maskmod_ds,
                                                                  contour_ds=self._bitmask_contour_ds,
                                                                  status=self._status_div ),
                                                       code=self._js['contour-maskmod'] + self._js_mode_code['bitmask-hotkey-setup-add-sub'] +
                                                            '''if ( cb_obj._mode == 'cube' ) mask_sub_cube( )
                                                               else mask_sub_chan( )''' )

        self._mask_add_sub['mask'].callback = CustomJS( args=dict( annotations=self._annotations,
                                                                   contour_ds=self._bitmask_contour_ds,
                                                                   mask_region_ds=self._bitmask_contour_maskmod_ds,
                                                                   region=self._bitmask_contour_maskmod,
                                                                   selector=self._bitmask_color_selector,
                                                                   mask_region_button=self._mask_add_sub['mask'],
                                                                   mask_region_icons=self._mask_icons_,
                                                                   source=self._image_source,
                                                                   status=self._status_div ),
                                                        code=self._js['contour-maskmod'] + self._js_mode_code['bitmask-hotkey-setup-add-sub'] +
                                                             '''if ( mask_region_button.icon == mask_region_icons['on'] ) maskmod_region_clear( )
                                                                else maskmod_region_set( region )''' )


        if self._slider:
            ###
            ### this code is here instead of in `def slider(...)` because we do not know if
            ### the user is using statistics until connect( ) is called...
            ### ... BUT we also need to handle statistics WITHOUT a slider... hmmm....
            ### ... NEED TO switch statistics updates to use _image_source.cur_chan instead...
            ### ... ALSO statistics would be based upon the SELECTION SET...
            ###
            self._cb['slider'] = CustomJS( args=dict( isource=self._image_source, slider=self._slider,
                                                      stats_source=self._statistics_source,
                                                      pixlabel = self._pixel_tracking_text,
                                                      min=self._cm_adjust['min input'],
                                                      max=self._cm_adjust['max input'],
                                                      span1=self._cm_adjust['span one'],
                                                      span2=self._cm_adjust['span two'],
                                                      histogram=self._cm_adjust['histogram'],
                                                      go_to=self._goto, cb=self._slider_callback,
                                                      ids=self._ids, ctrl=self._pipe['control'], pix_wrld=self._coord_ctrl_dropdown ),
                                           code=self._js['pixel-update-func'] + (self._js['slider_w_stats'] if self._statistics_source else self._js['slider_wo_stats']) )

            self._slider.js_on_change( 'value', self._cb['slider'] )

        if self._goto:
            self._goto_stokes.js_on_click( CustomJS( args=dict( source=self._image_source,
                                                                stokes=self._channel_ctrl_stokes_dropdown,
                                                                goto_stokes=self._goto_stokes ),
                                                     ### 'stokes.label' is updated after the channel has changed to allow for subsequent
                                                     ###  updates (e.g. convergence plot) to update based upon 'label' after fresh
                                                     ###  convergence data is available...
                                                     code= self._js['stokes-change'] % ( ' : '.join( map( lambda x: f'''cb_obj.item == '{x[1]}' ? {x[0]}''',
                                                                                         zip(range(len(self._stokes_labels)),self._stokes_labels) ) ) + ' : 0' ) ) )
            self._goto_txt.js_on_event( 'mouseenter', CustomJS( args=dict( slider=self._slider, dropdown=self._goto_stokes ),
                                                                code='''cb_obj.origin._has_focus = true
                                                                        const view = Bokeh.find.view(cb_obj.origin)
                                                                        view.input_el.focus( )
                                                                        cb_obj.origin.value = ''
                                                                        dropdown.label = "Go To"''' ) )
            self._goto_txt.js_on_event( 'mouseleave', CustomJS( args=dict( slider=self._slider, dropdown=self._goto_stokes,
                                                                           stokes=self._channel_ctrl_stokes_dropdown ),
                                                                code='''const view = Bokeh.find.view(slider)
                                                                        dropdown.label = `${stokes.label} Channel`
                                                                        document.activeElement.blur( )
                                                                        if ( slider ) cb_obj.origin.value = String(slider.value)
                                                                        cb_obj.origin._has_focus = false''' ) )

            self._goto_txt.js_on_event( ValueSubmit, CustomJS( args=dict( img=self._image_source,
                                                                          slider=self._slider,
                                                                          status=self._status_div ),
                                                               code='''let values = cb_obj.value.split(/[ ,]+/).map((v,) => parseInt(v))
                                                                       if ( values.length > 2 ) {
                                                                           status._error_set = true
                                                                           status.text = '<p>enter at most two indexes</p>'
                                                                       } else if ( values.filter((x) => x < 0 || isNaN(x)).length > 0 ) {
                                                                           status._error_set = true
                                                                           status.text = '<p>invalid channel entered</p>'
                                                                       } else {
                                                                           if ( status._error_set ) {
                                                                               status._error_set = false
                                                                               status.text = '<p/>'
                                                                           }
                                                                           if ( values.length == 1 ) {
                                                                               if ( values[0] >= 0 && values[0] < img.num_chans[1] ) {
                                                                                   status._error_set = false
                                                                                   status.text= `<p>moving to channel ${values[0]}</p>`
                                                                                   slider.value = values[0]
                                                                               } else {
                                                                                   status._error_set = true
                                                                                   status.text = `<p>channel ${values[0]} out of range</p>`
                                                                               }
                                                                           } else if ( values.length == 2 ) {
                                                                               if ( values[0] < 0 || values[0] >= img.num_chans[1] ) {
                                                                                   status._error_set = true
                                                                                   status.text = `<p>channel ${values[0]} out of range</p>`
                                                                               } else {
                                                                                   if ( values[1] < 0 || values[1] >= img.num_chans[0] ) {
                                                                                       status._error_set = true
                                                                                       status.text = `<p>stokes ${values[1]} out of range</p>`
                                                                                   } else {
                                                                                       status._error_set = false
                                                                                       status.text= `<p>moving to channel ${values[0]}/${values[1]}</p>`
                                                                                       slider.value = values[0]
                                                                                       img.channel( values[0], values[1] )
                                                                                   }
                                                                               }
                                                                           }
                                                                       }
                                                                       if ( ! status._error_set ) cb_obj.origin.value = "" ''' ) )


        if self._statistics_mask:
            self._statistics_mask.js_on_click( CustomJS( args=dict( source=self._image_source,
                                                                    stats_source=self._statistics_source,
                                                                    ids=self._ids,
                                                                    ctrl=self._pipe['control'] ),
                                                         ###
                                                         ### (1) send message to configure statistics behavior
                                                         ### (2) when reply is received change label and refresh channel display
                                                         ### (3) when reply is received update statistics
                                                         ###
                                                         code='''if ( cb_obj.item != cb_obj.origin.label ) {
                                                                     // >>>>---moving-to-mask-from-channel-----vvvvvvvvvvvvvvvvvvvv
                                                                     const masking_on = cb_obj.origin.label == 'Channel Statistics'
                                                                     ctrl.send( ids['config-statistics'],
                                                                                { action: 'use mask', value: masking_on },
                                                                                (msg) => { cb_obj.origin.label = cb_obj.item
                                                                                           source.channel( source.cur_chan[1], source.cur_chan[0],
                                                                                                           msg => { if ( 'stats' in msg ) { source.update_statistics( msg.stats ) } } ) } ) }
                                                         ''' ) )

        self._image.js_on_event( MouseEnter, CustomJS( args=dict( source=self._image_source,
                                                                  stats_source=self._statistics_source ),
                                                                  code= ( self._js['func-curmasks']( ) + self._js['key-state-funcs']
                                                                          if self._mask_path is None else "" ) +
                                                       '''casalib.hotkeys.setScope('channel')''' ) )
        self._image.js_on_event( MouseLeave, CustomJS( args=dict( source=self._image_source,
                                                                  stats_source=self._statistics_source ),
                                                                  code= ( self._js['func-curmasks']( ) + self._js['key-state-funcs']
                                                                          if self._mask_path is None else "" ) +
                                                       '''casalib.hotkeys.setScope( )''' ) )

        self._image_source.js_on_change( 'cur_chan', CustomJS( args=dict( slider=self._slider, label=self._channel_ctrl,
                                                                          stokes_label=self._channel_ctrl_stokes_dropdown ),
                                                               ### the label manipulation portion of 'code' is '' when self._channel_ctrl is None
                                                               ### so stokes_label.label and label.text will not be updated when they are not used
                                                               code=( ( '''label.text = `Channel ${cb_obj.cur_chan[1]}`
                                                                           stokes_label.label = ( %s );''' %
                                                                        ( ' : '.join(map( lambda p: f'''cb_obj.cur_chan[0] == {p[0]} ? '{p[1]}' ''',
                                                                                          zip( range(len(self._stokes_labels)), self._stokes_labels )) ) + " : ''" ) if
                                                                        self._channel_ctrl else '' ) +
                                                                      ( ( '''if ( casalib.hotkeys.getScope( ) === 'channel' ) slider.value = cb_obj.cur_chan[1]''' if
                                                                          self._slider else '') +
                                                                        (self._js['func-curmasks']('cb_obj') + self._js['add-polygon'])
                                                                        if self._mask_path is None else '' ) ) ) )

        if self._channel_ctrl:
            ###
            ### allow switching to stokes planes
            ###
            self._channel_ctrl_stokes_dropdown.menu = self._stokes_labels
            self._channel_ctrl_stokes_dropdown.js_on_click( CustomJS( args=dict( source=self._image_source,
                                                                                 stokes=self._channel_ctrl_stokes_dropdown,
                                                                                 goto_stokes=self._goto_stokes ),
                                                                       ### 'label' is updated after the channel has changed to allow for subsequent
                                                                       ###  updates (e.g. convergence plot) to update based upon 'label' after fresh
                                                                       ###  convergence data is available...
                                                                       code= self._js['stokes-change'] % ( ' : '.join( map( lambda x: f'''cb_obj.item == '{x[1]}' ? {x[0]}''',
                                                                                                         zip(range(len(self._stokes_labels)),self._stokes_labels) ) ) + ' : 0' ) ) )

        ###
        ### cursor movement code snippets
        movement_code_spectrum_update = ''
        movement_code_pixel_update = ''
        if self._spectrum:
            ###
            ### this is set up in connect( ) because slider must be updated if it is used othersize
            ### channel should be directly set (previously the slider was implicitly set when a new
            ### channel was selected, but I think this update was broken when the oscillation problem
            ### we fixed, see above)
            ###
            self._cb['sptap'] = CustomJS( args=dict( span=self._sp_span, source=self._image_source, slider=self._slider ),
                                          code = '''if ( span.location >= 0 ) {
                                                        if ( slider ) slider.value = span.location
                                                        else source.channel( span.location, source.cur_chan[0] )
                                                             //      chan----^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^-----stokes
                                                    }''' )

            self._spectrum.js_on_event('tap', self._cb['sptap'])

            ###
            ### code for spectrum update due to cursor movement
            ###
            movement_code_spectrum_update = """if ( cb_obj.event_type === 'move' ) {
                                                   if ( ctrl._freeze_cursor_update == false ) {
                                                       var geometry = cb_data['geometry']
                                                       var x_pos = Math.floor(geometry.x)
                                                       var y_pos = Math.floor(geometry.y)
                                                       if ( isFinite(x_pos) && isFinite(y_pos) && x_pos >= 0 && y_pos >= 0 ) {
                                                           isource._current_pos = [ x_pos, y_pos ]
                                                           if ( ! specfig.disabled && ! imagefig.disabled ) {
                                                               /* SEGV: cannot fetch pixels while tclean may be modifying the image */
                                                               update_spectrum( isource.cur_chan, [ x_pos, y_pos ],
                                                                                ( spec ) => specds.data = spec.spectrum )
                                                           }
                                                       }
                                                   }
                                               } else if ( cb_obj.event_name === 'mouseenter' ) {
                                                   ctrl._freeze_cursor_update = false
                                               }"""

        if self._pixel_tracking_text:
            ###
            ### code for updating pixel value due to cursor movements
            ###
            movement_code_pixel_update = self._js['pixel-update-func'] + '''
                                            if ( cb_obj.event_type === 'move' ) {
                                                if ( ctrl._freeze_cursor_update == false ) {
                                                    var geometry = cb_data['geometry']
                                                    var x_pos = Math.floor(geometry.x)
                                                    var y_pos = Math.floor(geometry.y)
                                                    if ( isFinite(x_pos) && isFinite(y_pos) && x_pos >= 0 && y_pos >= 0 ) {
                                                        isource._current_pos = [ x_pos, y_pos ]
                                                        if ( ! pixlabel.disabled ) {
                                                            /* SEGV: cannot fetch pixels while tclean may be modifying the image */
                                                            update_spectrum( isource.cur_chan, [ x_pos, y_pos ],
                                                                             ( spec ) => {
                                                                                 refresh_pixel_display( spec.index,
                                                                                                        spec.spectrum.y[spec.chan[1]],
                                                                                                        'mask' in spec && spec.mask[spec.chan[1]],
                                                                                                        pix_wrld && pix_wrld.label == 'pixel' ? false : true )
                                                                             } )
                                                        }
                                                    }
                                                }
                                            }'''

        if movement_code_spectrum_update or movement_code_pixel_update:
            self._cb['impos'] = CustomJS( args=dict( specds=self._image_spectrum, specfig=self._spectrum, imagefig=self._image,
                                                     isource=self._image_source, ids=self._ids, ctrl=self._pipe['control'],
                                                     pixlabel = self._pixel_tracking_text, pix_wrld=self._coord_ctrl_dropdown ),
                                          code = movement_code_spectrum_update + movement_code_pixel_update )

            self._hover['image'] = HoverTool( callback=self._cb['impos'], tooltips=None )

            self._image.js_on_event('mouseenter',self._cb['impos'])
            self._image.add_tools(self._hover['image'])


        ## this is in the connect function to allow for access to self._statistics_source
        self._image_source.init_script = CustomJS( args=dict( annotations=self._annotations, ctrl=self._pipe['control'], ids=self._ids,
                                                              stats_source=self._statistics_source, chan_slider=self._slider,
                                                              mask_region_button=self._mask_add_sub['mask'],
                                                              mask_region_icons=self._mask_icons_,
                                                              mask_region_ds=self._bitmask_contour_maskmod_ds,
                                                              contour_ds=self._bitmask_contour_ds,
                                                              status=self._status_div, statprec=7 ),
                                                              code='''let source = cb_obj;''' +
                                                                   ( self._js['mask-state-init'] + self._js['func-curmasks']( ) +
                                                                     self._js['contour-maskmod'] +
                                                                     self._js['key-state-funcs'] + self._js['setup-key-mgmt']
                                                                     if self._mask_path is None else self._js['contour-maskmod'] + self._js['setup-key-mgmt'] ) +
                                                                   """// This function is called to collect the masks and/or stop
                                                                      // -->> collect_masks( ) is only defined if bitmask cube is NOT used
                                                                      source.done = ( ) => {
                                                                          function done_close_window( msg ) {
                                                                              if ( msg.result === 'stopped' ) {""" +
                                                                            # Don't close tab if running in a jupyter notebook
                                                                            ("""console.log("Running in jupyter notebook. Not closing window.")""" if self._is_notebook else
                                                                                 """console.log("Running from script/terminal. Closing window.")
                                                                                    window.close()"""
                                                                            ) +
                                                                    """
                                                                              }
                                                                          }
                                                                          ctrl.send( ids['done'],
                                                                                     { action: 'done',
                                                                                       value: typeof collect_masks == 'function' ? collect_masks( ) : { masks: [], polys: [] } },
                                                                                     done_close_window )
                                                                      }
                                                                      // exported functions -- enable/disable masking, retrieve masks etc.
                                                                      source._masking_enabled = true
                                                                      source.disable_masking = ( ) => source._masking_enabled = false
                                                                      source.enable_masking = ( ) => source._masking_enabled = true
                                                                      source.masks = ( ) => typeof collect_masks == 'function' ? collect_masks( ) : null
                                                                      source.breadcrumbs = ( ) => typeof source._mask_breadcrumbs !== 'undefined' ? source._mask_breadcrumbs : null
                                                                      source.drop_breadcrumb = ( code ) => source._mask_breadcrumbs += code
                                                                      source.update_statistics = ( data ) => {
                                                                          data.values.forEach( (item, index) => {
                                                                              /** round floats **/
                                                                              if ( typeof item == 'number' && ! Number.isInteger(item) ) {
                                                                                  data.values[index] = Math.round((item + Number.EPSILON) * 10**statprec) / 10**statprec
                                                                              } } )
                                                                          stats_source.data = data
                                                                      }
                                                                      source.update_statistics( stats_source.data ) /*** round floats ***/
                                                                   """ )

        ###
        ### This setup is delayed until connect( ) to allow for the use of
        ### self._bitmask_color_selector
        ###
        if self._bitmask_color_selector:
            self._bitmask_color_selector.js_on_change( 'color', CustomJS( args=dict( bitmask=self._bitmask,
                                                                                     contour=self._bitmask_contour,
                                                                                     region=self._bitmask_contour_maskmod,
                                                                                     bitrep=self._bitmask_transparency_button,
                                                                                     annotations=self._annotations ),
                                                         code= ( "" if self._mask_path is None else
                                                                 '''annotations[0].line_color = cb_obj.color;''' ) +
                                                                 '''let cm = bitmask.glyph.color_mapper
                                                                    if ( bitmask._transparent == null ) {
                                                                        bitmask._transparent = cm.palette[0]
                                                                    }
                                                                    if ( bitrep.label == 'masked' ) {
                                                                        cm.palette[1] = cb_obj.color
                                                                    } else if ( bitrep.label == 'unmasked' ) {
                                                                        cm.palette[0] = cb_obj.color
                                                                    }
                                                                    cm.change.emit( )
                                                                    contour.glyph.line_color = cb_obj.color
                                                                    region.glyph.line_color = cb_obj.color''' ) )

        self._image.js_on_event( SelectionGeometry,
                                 CustomJS( args=dict( source=self._image_source,
                                                      annotations=self._annotations,
                                                      selector=self._bitmask_color_selector,
                                                      mask_region_button=self._mask_add_sub['mask'],
                                                      mask_region_icons=self._mask_icons_,
                                                      contour_ds=self._bitmask_contour_ds,
                                                      mask_region_ds=self._bitmask_contour_maskmod_ds ),
                                           code= ( self._js['func-newpoly'] + self._js['func-curmasks']( ) + self._js['contour-maskmod'] +
                                                   self._js['mask-state-init'] + self._js_mode_code['no-bitmask-tool-selection'] )
                                                   if self._mask_path is None else  self._js['contour-maskmod'] + (
                                                   ### selector indicates if a on-disk mask is being used
                                                   '''if ( source._masking_enabled ) {
                                                          const geometry = cb_obj['geometry']
                                                          if ( geometry.type === 'rect' ) {
                                                              // rectangle drawing complete
                                                              maskmod_region_set( annotations[0],
                                                                                  [ geometry.x0, geometry.x0, geometry.x1, geometry.x1 ],
                                                                                  [ geometry.y0, geometry.y1, geometry.y1, geometry.y0 ] )
                                                          } else if ( geometry.type === 'poly' && cb_obj.final ) {
                                                              // polygon drawing complete
                                                              maskmod_region_set( annotations[0],
                                                                                  [ ].slice.call(geometry.x),
                                                                                  [ ].slice.call(geometry.y) )
                                                          }
                                                      }''' ) ) )


    def js_obj( self ):
        '''return the javascript object that can be used for control. This
        object should contain a ``done`` function which will cause the
        masking GUI to exit and return the masks that have been drawn
        Also provides JavaScript functions:
            disable_masking( )
            enable_masking( )
        '''
        if not self._image_source:
            raise RuntimeError('an image widget must be created (with CubeMask.image) before js_obj( ) can be called')
        return self._image_source

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
        return self._result

    def help( self, rows=[ ], **kw ):
        '''Retrieve the help Bokeh object. When this button is clicked, a tab/window
        containing the help information is opened or receives focus.
        '''
        if self._help_button is None:
            self._help_button = set_attributes( TipButton( label="", max_width=35, max_height=35, name='help',
                                                           button_type='light', hover_wait=0, margin=(-1, 0, 0, 0),
                                                           tooltip=Tooltip( content=HTML( '''<b>Click</b> here for image command key help.
                                                                                             <b>Hover</b> over some widgets for 1.5 seconds for other help''' ),
                                                                            position="bottom" ) ), **kw )
            self._help_button.js_on_click( CustomJS( args=dict( text=self.__help_string( ) ),
                                                     code='''if ( window._iclean_help && ! window._iclean_help.closed ) {
                                                                 window._iclean_help.focus( )
                                                             } else {
                                                                 window._iclean_help = window.open("about:blank","Interactive Clean Help")
                                                                 window._iclean_help.document.write(text)
                                                                 window._iclean_help.document.close( )
                                                             }''' ) )
        return self._help_button

    @asynccontextmanager
    async def serve( self, stop_function ):
        self._stop_serving_function = stop_function
        async with websockets.serve( self._pipe['image'].process_messages, self._pipe['image'].address[0], self._pipe['image'].address[1] ) as im, \
             websockets.serve( self._pipe['control'].process_messages, self._pipe['control'].address[0], self._pipe['control'].address[1] ) as ctrl:
            yield { 'im': im, 'ctrl': ctrl }

    def __help_string( self, rows=[ ] ):
        '''Retrieve the help Bokeh object. When returned the ``visible`` property is
        set to ``False``, but it can be toggled based on GUI actions.
        '''
        mask_control = { 'no-mask': '''
                             <tr><td><b>option</b></td><td>display mask cursor (<i>at least one mask must have been drawn</i>)</td></tr>
                             <tr><td><b>option</b>-<b>]</b></td><td>move cursor to next mask</td></tr>
                             <tr><td><b>option</b>-<b>[</b></td><td>move cursor to previous mask</td></tr>
                             <tr><td><b>option</b>-<b>/</b></td><td>add mask to selection set</td></tr>
                             <tr><td><b>option</b>-<b>escape</b></td><td>clear selection set</td></tr>
                             <tr><td><b>down</b></td><td>move selection set down one pixel</td></tr>
                             <tr><td><b>up</b></td><td>move selection set up one pixel</td></tr>
                             <tr><td><b>left</b></td><td>move selection one pixel to the left</td></tr>
                             <tr><td><b>right</b></td><td>move selection one pixel to the right</td></tr>
                             <tr><td><b>shift</b>-<b>up</b></td><td>move selection up several pixels</td></tr>
                             <tr><td><b>shift</b>-<b>down</b></td><td>move selection down several pixels</td></tr>
                             <tr><td><b>shift</b>-<b>left</b></td><td>move selection several pixels to the left</td></tr>
                             <tr><td><b>shift</b>-<b>right</b></td><td>move selection several pixels to the right</td></tr>
                             <tr><td><b>option</b>-<b>c</b></td><td>copy selection set to the copy buffer</td></tr>
                             <tr><td><b>option</b>-<b>v</b></td><td>paste selection set into the current channel</td></tr>
                             <tr><td><b>option</b>-<b>shift</b>-<b>v</b></td><td>paste selection set into all channels along the current stokes axis</td></tr>
                             <tr><td><b>option</b>-<b>delete</b></td><td>delete polygon indicated by the cursor</td></tr>''',
                         'mask': '''
                             <tr><td><b>f</b></td><td>freeze cursor tracking updates until the mouse <b>re-enters</b> the channel plot</td></tr>
                             <tr><td><b>a</b></td><td>add region to the mask for the current channel</td></tr>
                             <tr><td><b>s</b></td><td>subtract region from the mask for the current channel</td></tr>
                             <tr><td><b>shift</b>-<b>a</b></td><td>add region to the mask for all channels</td></tr>
                             <tr><td><b>shift</b>-<b>s</b></td><td>subtract region from the mask for all channels</td></tr>
                             <tr><td><b>~</b></td><td>invert mask values for the current channel</td></tr>
                             <tr><td><b>!</b></td><td>invert mask values for all channels</td></tr>
                             <tr><td><b>escape</b></td><td>unselect the selected region</td></tr>
                             <tr><td><b>down</b></td><td>move selected region down one pixel</td></tr>
                             <tr><td><b>up</b></td><td>move selected region up one pixel</td></tr>
                             <tr><td><b>left</b></td><td>move selected region one pixel to the left</td></tr>
                             <tr><td><b>right</b></td><td>move selected region one pixel to the right</td></tr>
                             <tr><td><b>shift</b>-<b>up</b></td><td>move selected region up several pixels</td></tr>
                             <tr><td><b>shift</b>-<b>down</b></td><td>move selected region down several pixels</td></tr>
                             <tr><td><b>shift</b>-<b>left</b></td><td>move selected region several pixels to the left</td></tr>
                             <tr><td><b>shift</b>-<b>right</b></td><td>move selected region several pixels to the right</td></tr>'''
                         }

        return \
'''<html>
  <head>
    <title>Interactive Clean Help</title>
    <style>
        #makemaskhelp td, #makemaskhelp th {
            border: 1px solid #ddd;
            text-align: left;
            padding: 8px;
        }
        #makemaskhelp tr:nth-child(even){background-color: #f2f2f2}
    </style>
  </head>
  <body>
    <table id="makemaskhelp">
      <tr><th>buttons/key(s)</th><th>description</th></tr>
      EXTRAROWS
      <tr><td><b>option</b>-<b>up</b></td><td>to next channel (<b>ctrl</b> or <b>cmd</b> can be used)</td></tr>
      <tr><td><b>option</b>-<b>down</b></td><td>to previous channel (<b>ctrl</b> or <b>cmd</b> can be used)</td></tr>
      <tr><td><b>option</b>-<b>right</b></td><td>to next stokes axis (<b>ctrl</b> or <b>cmd</b> can be used)</td></tr>
      <tr><td><b>option</b>-<b>left</b></td><td>to previous stokes axis (<b>ctrl</b> or <b>cmd</b> can be used)</td></tr>
      MASKCONTROL
    </table>
  </body>
</html>'''.replace('option','option' if platform == 'darwin' else 'alt') \
          .replace('<b>delete</b>','<b>delete</b>' if platform == 'darwin' else '<b>backspace</b>') \
          .replace('EXTRAROWS','\n'.join(rows)) \
          .replace('MASKCONTROL', mask_control['no-mask'] if self._mask_path is None else mask_control['mask'])
