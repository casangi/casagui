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
'''This provides an implementation of ``CubeMask`` which allows interactive
clean and makemask to share a common implementaton. The user calls member
functions to create widgets which can be placed in the GUI created by the
calling application. Once all of the widgets have been created. The
``connect`` member function creates all of the Bokeh/JavaScript callbacks
that allow the widgets to interact'''

import asyncio
from uuid import uuid4
from sys import platform
import websockets
from bokeh.events import SelectionGeometry
from bokeh.models import CustomJS, Slider, PolyAnnotation, Div, Span, HoverTool, TableColumn, DataTable
from bokeh.plotting import ColumnDataSource, figure
from casagui.utils import find_ws_address, set_attributes
from casagui.bokeh.sources import ImageDataSource, SpectraDataSource, ImagePipe, DataPipe
from casagui.bokeh.state import initialize_bokeh
from ..utils import resource_manager

class CubeMask:
    '''Class which provides a common implementation of Bokeh widget behavior for
    interactive clean and make mask'''

    def __init__( self, image, abort=None ):
        '''Create a cube masking GUI which includes the 2-D raster cube plane display
        along with these optional components:

        *  slider to move through planes
        *  spectra plot (in response to mouse movements in 2-D raster display)
        *  statistics (table)

        Parameters
        ----------
        image: str
            path to CASA image for which interactive masks will be drawn
        abort: function
            If provided, the ``abort`` function will be called to exit the
            event loop in the case of an error.
        '''
        initialize_bokeh( )

        self._image_path = image	                # path to image cube to be displayed
        self._image = None		                # figure displaying cube planes
        self._slider = None		                # slider to move from plane to plane
        self._spectra = None		                # figure displaying spectra along the frequency axis
        self._statistics = None                         # statistics data table
        self._help = None
        self._image_spectra = None                      # spectra data source
        self._image_source = None	                # ImageDataSource
        self._statistics_source = None
        self._pipe = { 'image': None, 'control': None } # data pipes
        self._ids = { 'done': str(uuid4( )) }           # ids used for control messages

        self._fig = { }
        self._hover = { 'spectra': None, 'image': None }# HoverTools which are used to synchronize image/spectra
                                                        # movement/taps and and corresponding display

        self._result = None                             # result to be filled in from Bokeh

        self._image_server = None
        self._control_server = None

        self._mask = { }		                # mask drawing
        self._cb = { }
        self._annotations = [ ]		                # statically allocate fixed poly annotations for (re)use
                                                        # on successive image cube planes

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
        self._js = { ### update stats in response to channel changes
                     ### -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
                     ### The slider and the events from the update of the image source are
                     ### coupled because the image cube channel can be changed outside of the
                     ### slider context. However, allowing the slider value to be updated via
                     ### the update to the cube update can cause oscillations when the slider
                     ### is moved very quickly [slider causes channel change, channel change
                     ### causes slider value to be set]. To prevent this,
                     ### slider._processing_count is used to prevent the slider value from
                     ### being set in response to the channel update when it was the slider
                     ### that initiated the update chain.
                     'slider_w_stats':  '''slider._processing_count = slider._processing_count ? slider._processing_count + 1 : 1
                                           source.channel( slider.value, 0, msg => { if ( 'stats' in msg ) { stats_source.data = msg.stats } } )''',
                     'slider_wo_stats': '''slider._processing_count = slider._processing_count ? slider._processing_count + 1 : 1
                                           source.channel( slider.value, 0 )''',
                     ### setup maping of keys to numeric values
                     'keymap-init':     '''const keymap = { up: 38, down: 40, left: 37, right: 39, control: 17,
                                                            option: 18, next: 78, prev: 80, escape: 27, space: 32,
                                                            command: 91, copy: 67, paste: 86, delete: 8, shift: 16 };''',
                     ### initialize mask state
                     ###
                     ### mask breadcrumbs
                     ###    '
                     'mask-state-init': '''if ( typeof(source._mask_breadcrumbs) === 'undefined' ) {
                                               source._mask_breadcrumbs = ''
                                           }
                                           if ( typeof(source._cur_chan_prev) === 'undefined' ) {
                                               source._cur_chan_prev = source.cur_chan
                                           }
                                           if ( typeof(source._polys) === 'undefined' ) {
                                               source._polys = [ ]              //  [ { id: int,
                                                                                //      type: string,
                                                                                //      geometry: { xs: [ float, ... ], ys: [ float, ... ] } } ]
                                               source._cursor_color = 'red'
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

                                               // set Xs for the current annotation add any X translation from current poly
                                               mask_annotation.xs = mask_poly.geometry.xs.reduce( (acc,x) => { acc.push(x + xlate[0]); return acc } , [ ] )
                                               // set Ys for the current annotation add any Y translation from current poly
                                               mask_annotation.ys = mask_poly.geometry.ys.reduce( 
                                                                        (acc,y) => { acc.push(y + xlate[1]); return acc } , [ ] )
                                                                        // restore selections for this channel
                                                                        if ( cur_masks[3].includes( i ) ) mask_annotation.fill_color = cb_obj._cursor_color
                                                                    } )
                                               cb_obj._cur_chan_prev = cb_obj.cur_chan''',
                     ### invoke key state management functions in response to keyboard events in the document. this
                     ### code manages the permitted key combinations while most of the state management is handled
                     ### by the state management functions.
                     'setup-key-mgmt':  '''if ( typeof(document._key_state) === 'undefined' ) {
                                               document._key_state = { option: false, control: false, shift: false }
                                               document.addEventListener( 'keydown',
                                                   (e) => { if ( e.keyCode === keymap.shift ) {
                                                                // shift key is independent of the control/option state
                                                                document._key_state.shift = true
                                                            } else if ( document._key_state.option === true ) {     // option key
                                                                e.preventDefault()                                  // prevent default key behavior
                                                                if ( document._key_state.control === true ) {       // control key
                                                                                                                    // arrow (no opt key) up moves through channels
                                                                    if ( e.keyCode === keymap.up ) {
                                                                        const prev_masks = curmasks( )
                                                                        let cur_masks = null
                                                                        if ( source.cur_chan[1] + 1 >= source.num_chans[1] ) {
                                                                            // wrap round to the first channel
                                                                            source.channel( 0, source.cur_chan[0] )
                                                                            cur_masks = curmasks( [ source.cur_chan[0], 0 ] )
                                                                        } else {
                                                                            // advance to the next channel
                                                                            source.channel( source.cur_chan[1] + 1, source.cur_chan[0] )
                                                                            cur_masks = curmasks( [ source.cur_chan[0], source.cur_chan[1] + 1 ] )
                                                                        }
                                                                    } else if ( e.keyCode === keymap.down ) {
                                                                        if ( source.cur_chan[1] - 1 >= 0 ) {
                                                                            // advance to the prev channel
                                                                            source.channel( source.cur_chan[1] - 1, source.cur_chan[0] )
                                                                        } else {
                                                                            // wrap round to the last channel
                                                                            source.channel( source.num_chans[1] - 1, source.cur_chan[0] )
                                                                        }
                                                                    }
                                                                }                                              // control key
                                                                else {                                         // no control key
                                                                    const shape = source.image_source.shape
                                                                    const shifted = document._key_state.shift
                                                                    if ( e.keyCode === keymap.control ) {
                                                                        let cm = curmasks( )
                                                                        if ( document._key_state.option )
                                                                            state_clear_cursor( cm )
                                                                            document._key_state.control = true
                                                                            state_clear_cursor( cm )
                                                                        } else if ( e.keyCode === keymap.next ) {
                                                                            state_next_cursor( )
                                                                        } else if ( e.keyCode === keymap.prev ) {
                                                                            state_prev_cursor( )
                                                                        } else if ( e.keyCode === keymap.space ) {
                                                                            let cm = curmasks( )
                                                                            state_cursor_to_selection( cm )
                                                                        } else if ( e.keyCode === keymap.escape ) {
                                                                            state_clear_selection( )
                                                                        } else if ( e.keyCode === keymap.delete ) {
                                                                            // remove cursor mask from channel
                                                                            state_remove_mask( )
                                                                        } else if ( e.keyCode === keymap.up ) {
                                                                            state_translate_selection( 0, shifted ? Math.floor(shape[1]/10) : 1 )
                                                                        } else if ( e.keyCode === keymap.down ) {
                                                                            state_translate_selection( 0, shifted ? -Math.floor(shape[1]/10) : -1 )
                                                                        } else if ( e.keyCode === keymap.left ) {
                                                                            state_translate_selection( shifted ? -Math.floor(shape[0]/10) : -1, 0 )
                                                                        } else if ( e.keyCode === keymap.right ) {
                                                                            state_translate_selection( shifted ? Math.floor(shape[0]/10) : 1, 0 )
                                                                        } else if ( e.keyCode === keymap.copy ) {
                                                                            state_copy_selection( )
                                                                        } else if ( e.keyCode === keymap.paste ) {
                                                                            if ( document._key_state.shift ) {
                                                                                register_mask_change('V')
                                                                                for ( let stokes=0; stokes < source._chanmasks.length; ++stokes ) {
                                                                                    for ( let chan=0; chan < source._chanmasks[stokes].length; ++chan ) {
                                                                                        if ( stokes != source._copy_buffer[1][0] ||
                                                                                             chan != source._copy_buffer[1][1] )
                                                                                            state_paste_selection( curmasks( [ stokes, chan ] ) )
                                                                                    }
                                                                                }
                                                                            } else {
                                                                                register_mask_change('v')
                                                                                state_paste_selection( )
                                                                            }
                                                                        }
                                                                    }                                              // no control key
                                                            } else {                                               // no option key
                                                                    // option key first pressed
                                                                    if ( e.keyCode === keymap.option ) {
                                                                        document._key_state.option = true
                                                                        if ( document._key_state.control !== true ) state_initialize_cursor( )
                                                                    }
                                                                    else if ( e.keyCode === keymap.control ) {
                                                                        document._key_state.control = true
                                                                    }
                                                            }                                                  // no option key
                                                          } )
                                               document.addEventListener( 'keyup',
                                                   (e) => { // option key released
                                                            if ( e.keyCode === keymap.option ) {
                                                                document._key_state.option = false
                                                                state_clear_cursor( )
                                                            } else if ( e.keyCode === keymap.control ) {
                                                                document._key_state.control = false
                                                                if ( document._key_state.option === true )
                                                                    state_initialize_cursor( )
                                                            } else if ( e.keyCode === keymap.shift ) {
                                                                document._key_state.shift = false
                                                            }
                                                          } )
                                           }'''
                        }

    def __stop( self ):
        '''stop interactive masking
        '''
        resource_manager.stop_asyncio_loop()
        if self._image_server is not None and self._image_server.ws_server.is_serving( ):
            resource_manager.stop_asyncio_loop()
        if self._control_server is not None and self._control_server.ws_server.is_serving( ):
            resource_manager.stop_asyncio_loop()

    def _init_pipes( self ):
        '''set up websockets
        '''
        if self._pipe['image'] is None:
            self._pipe['image'] = ImagePipe(image=self._image_path, stats=True, abort=self.__abort, address=find_ws_address( ))
        if self._pipe['control'] is None:
            self._pipe['control'] = DataPipe(address=find_ws_address( ), abort=self.__abort)

    def path( self ):
        '''return path to CASA image
        '''
        return self._image_papth

    def jsmask_to_raw( self, jsmask ):
        '''The CubeMask raw format uses tuples for dictionary keys but tuples are not a type that can be
        created in javascript...
        '''
        def convert_elem( vec, f=lambda x: x ):
            return { f(chan_or_poly[0]): chan_or_poly[1] for chan_or_poly in vec }
        return { 'masks': convert_elem(jsmask['masks'],tuple), 'polys': convert_elem(jsmask['polys']) }

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

            self._annotations = [ PolyAnnotation( xs=[], ys=[], fill_alpha=0.1, line_color=None, fill_color='black', visible=True ) for _ in range(maxanno) ]

            self._pipe['control'].register( self._ids['done'], receive_return_value )
            self._image_source = ImageDataSource( image_source=self._pipe['image'],
                                                  init_script=CustomJS( args=dict( annotations=self._annotations, ctrl=self._pipe['control'], ids=self._ids ),
                                                                        code='let source = cb_obj;' + self._js['mask-state-init'] + self._js['keymap-init'] +
                                                                             self._js['func-curmasks']( ) + self._js['key-state-funcs'] +
                                                                             self._js['setup-key-mgmt'] +
                                                                             """// This function is called to collect the masks and/or stop
                                                                                source.done = ( ) => {
                                                                                    function done_close_window( msg ) {
                                                                                        if ( msg.result === 'stopped' ) {
                                                                                            window.close()
                                                                                        }
                                                                                    }
                                                                                    ctrl.send( ids['done'],
                                                                                               { action: 'done', value: collect_masks( ) },
                                                                                               done_close_window )
                                                                                }
                                                                                // exported functions -- enable/disable masking, retrieve masks etc.
                                                                                source._masking_enabled = true
                                                                                source.disable_masking = ( ) => source._masking_enabled = false
                                                                                source.enable_masking = ( ) => source._masking_enabled = true
                                                                                source.masks = ( ) => collect_masks( )
                                                                                source.breadcrumbs = ( ) => source._mask_breadcrumbs
                                                                                source.drop_breadcrumb = ( code ) => register_mask_change( code )
                                                                    """) )

            self._image = set_attributes( figure( output_backend="webgl",
                                                  tools=[ "poly_select", "lasso_select","box_select","pan,wheel_zoom","box_zoom",
                                                          "save","reset" ],
                                                  tooltips=None ), **kw )

            self._image.x_range.range_padding = self._image.y_range.range_padding = 0

            shape = self._pipe['image'].shape
            self._image.image( image="d", x=0, y=0,
                                   dw=shape[0], dh=shape[1],
                                   palette="Spectral11",
                                   level="image", source=self._image_source )

            self._image.grid.grid_line_width = 0.5
            self._image.plot_height = 400
            self._image.plot_width = 400

            self._image.js_on_event( SelectionGeometry,
                                         CustomJS( args=dict( source=self._image_source,
                                                              annotations=self._annotations ),
                                                   code=self._js['func-newpoly'] + self._js['func-curmasks']( ) + self._js['mask-state-init'] +
                                                        """if ( source._masking_enabled ) {
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
                                                           }""" ) )

            for annotation in self._annotations:
                self._image.add_layout(annotation)

        return self._image

    def slider( self, **kw ):
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
            if slider_end == 0:
                # for a cube with one channel, a slider is of no use
                self._slider.disabled = True

        return self._slider

    def spectra( self, **kw ):
        '''Return the line graph of spectra from the image cube which is updated
        in response to moving the cursor within the 2D raster display.

        Parameters
        ----------
        kw: keyword and value
            extra keyword/value paramaters passed on to ``figure``
        '''
        if self._spectra is None:
            if self._image is None:
                ###
                ### an exception is raised instead of just creating the image display because if we create
                ### it here [by calling self.image( )], the user will silently lose the ability to set the
                ### maximum number of annotations per channel (along with other future parameters)
                ###
                raise RumtimeError('spectra( ) requires an image cube display, but one has not yet been created')

            self._image_spectra = SpectraDataSource(image_source=self._pipe['image'])

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

            self._hover['spectra'] = HoverTool( callback=self._cb['sppos'] )

            self._spectra = set_attributes( figure( plot_height=180, plot_width=800,
                                                    title="Spectrum", tools=[ self._hover['spectra'] ] ), **kw )
            self._spectra.add_layout(self._sp_span)

            self._cb['sptap'] = CustomJS( args=dict( span=self._sp_span, source=self._image_source ),
                                          code = '''if ( span.location >= 0 ) {
                                                        source.channel( span.location, source.cur_chan[0] )
                                                        //      chan----^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^-----stokes
                                                    }''' )

            self._spectra.js_on_event('tap', self._cb['sptap'])

            self._spectra.x_range.range_padding = self._spectra.y_range.range_padding = 0
            self._spectra.line( x='x', y='y', source=self._image_spectra )
            self._spectra.grid.grid_line_width = 0.5

            self._cb['impos'] = CustomJS( args=dict( specds=self._image_spectra, specfig=self._spectra, imagefig=self._image,
                                                     state=dict(frozen=False) ),
                                          code = """if ( ! specfig.disabled && ! imagefig.disabled ) {
                                                        if ( cb_obj.event_type === 'move' && state.frozen !== true ) {
                                                            var geometry = cb_data['geometry'];
                                                            var x_pos = Math.floor(geometry.x);
                                                            var y_pos = Math.floor(geometry.y);
                                                            specds.spectra(x_pos,y_pos)
                                                            if ( isFinite(x_pos) && isFinite(y_pos) ) {
                                                                specfig.title.text = `Spectrum (${x_pos},${y_pos})`
                                                            } else {
                                                                specfig.title.text = 'Spectrum'
                                                            }
                                                        } else if ( cb_obj.event_name === 'mouseenter' ) {
                                                            state.frozen = false
                                                        } else if ( cb_obj.event_name === 'tap' ) {
                                                            state.frozen = true
                                                        }
                                                    }""" )

            self._hover['image'] = HoverTool( callback=self._cb['impos'], tooltips=None )

            self._image.js_on_event('mouseenter',self._cb['impos'])
            self._image.js_on_event('tap',self._cb['impos'])
            self._image.add_tools(self._hover['image'])

        return self._spectra

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
            self._statistics = set_attributes( DataTable( source=self._statistics_source, columns=stats_column,
                                                          width=400, height=200, autosize_mode='none' ), **kw )

        return self._statistics

    def connect( self ):
        '''Connect the callbacks which are used by the masking GUIs that
        have been created.
        '''
        if self._slider:
            ###
            ### this code is here instead of in `def slider(...)` because we do not know if
            ### the user is using statistics until connect( ) is called...
            ### ... BUT we also need to handle statistics WITHOUT a slider... hmmm....
            ### ... NEED TO switch statistics updates to use _image_source.cur_chan instead...
            ### ... ALSO statistics would be based upon the SELECTION SET...
            ###
            self._cb['slider'] = CustomJS( args=dict( source=self._image_source, slider=self._slider,
                                                      stats_source=self._statistics_source ),
                                           code=self._js['slider_w_stats'] if self._statistics_source else self._js['slider_wo_stats'] )
            self._slider.js_on_change( 'value', self._cb['slider'] )

        self._image_source.js_on_change( 'cur_chan', CustomJS( args=dict( slider=self._slider ),
                                                               code=('''if ( slider._processing_count > 0 )
                                                                            slider._processing_count--
                                                                        else slider.value = cb_obj.cur_chan[1]''' if self._slider else '') +
                                                                    self._js['func-curmasks']('cb_obj') + self._js['add-polygon'] ) )

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
        '''Retrieve the help Bokeh object. When returned the ``visible`` property is
        set to ``False``, but it can be toggled based on GUI actions.
        '''
        if self._help is None:
            # using set_attributes allows the user to override defaults like 'width=650'
            self._help =set_attributes(
                Div( text='''<style>
                                 #makemaskhelp td, #makemaskhelp th {
                                     border: 1px solid #ddd;
                                     text-align: left;
                                     padding: 8px;
                                 }
                                 #makemaskhelp tr:nth-child(even){background-color: #f2f2f2}
                             </style>
                             <table id="makemaskhelp">
                               <tr><th>buttons/key(s)</th><th>description</th></tr>
                               EXTRAROWS
                               <tr><td><b>option</b></td><td>display mask cursor (<i>at least one mask must have been drawn</i>)</td></tr>
                               <tr><td><b>option</b>-<b>n</b></td><td>move cursor to next mask</td></tr>
                               <tr><td><b>option</b>-<b>p</b></td><td>move cursor to previous mask</td></tr>
                               <tr><td><b>option</b>-<b>space</b></td><td>add mask to selection set</td></tr>
                               <tr><td><b>option</b>-<b>escape</b></td><td>clear selection set</td></tr>
                               <tr><td><b>option</b>-<b>down</b></td><td>move selection set down one pixel</td></tr>
                               <tr><td><b>option</b>-<b>up</b></td><td>move selection set up one pixel</td></tr>
                               <tr><td><b>option</b>-<b>left</b></td><td>move selection one pixel to the left</td></tr>
                               <tr><td><b>option</b>-<b>right</b></td><td>move selection one pixel to the right</td></tr>
                               <tr><td><b>option</b>-<b>shift</b>-<b>up</b></td><td>move selection up several pixels</td></tr>
                               <tr><td><b>option</b>-<b>shift</b>-<b>down</b></td><td>move selection down several pixels</td></tr>
                               <tr><td><b>option</b>-<b>shift</b>-<b>left</b></td><td>move selection several pixels to the left</td></tr>
                               <tr><td><b>option</b>-<b>shift</b>-<b>right</b></td><td>move selection several pixels to the right</td></tr>
                               <tr><td><b>option</b>-<b>control</b>-<b>up</b></td><td>to next channel</td></tr>
                               <tr><td><b>option</b>-<b>control</b>-<b>down</b></td><td>to previous channel</td></tr>
                               <tr><td><b>option</b>-<b>control</b>-<b>right</b></td><td>to next stokes axis</td></tr>
                               <tr><td><b>option</b>-<b>control</b>-<b>left</b></td><td>to previous stokes axis</td></tr>
                               <tr><td><b>option</b>-<b>c</b></td><td>copy selection set to the copy buffer</td></tr>
                               <tr><td><b>option</b>-<b>v</b></td><td>paste selection set into the current channel</td></tr>
                               <tr><td><b>option</b>-<b>shift</b>-<b>v</b></td><td>paste selection set into all channels along the current stokes axis</td></tr>
                               <tr><td><b>option</b>-<b>delete</b></td><td>delete polygon indicated by the cursor</td></tr>
                           </table>'''.replace('option','option' if platform == 'darwin' else 'alt')
                                      .replace('<b>delete</b>','<b>delete</b>' if platform == 'darwin' else '<b>backspace</b>')
                                      .replace('EXTRAROWS','\n'.join(rows)),
                     visible=False, width=650 ), **kw )
        return self._help

    def loop( self ):
        '''Returns an ``asyncio`` eventloop which can be mixed in with an
        existing eventloop to animate this GUI.'''
        async def async_loop( loop1, loop2 ):
            return await asyncio.gather( loop1, loop2 )
        self._image_server = websockets.serve( self._pipe['image'].process_messages, self._pipe['image'].address[0], self._pipe['image'].address[1] )
        self._control_server = websockets.serve( self._pipe['control'].process_messages, self._pipe['control'].address[0], self._pipe['control'].address[1] )
        resource_manager.reg_webserver(self._image_server.ws_server)
        resource_manager.reg_webserver(self._control_server.ws_server)
        return async_loop( self._control_server, self._image_server )
