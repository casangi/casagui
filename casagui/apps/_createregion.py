########################################################################
#
# Copyright (C) 2024,2025
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
'''implementation of the ``CreateRegion`` application for interactive creation
of astropy regions'''

from os.path import exists, splitext, join
from os.path import split as splitpath
import asyncio
from contextlib import asynccontextmanager
from bokeh.layouts import row, column, grid
from bokeh.plotting import show
from bokeh.models import Button, CustomJS, TabPanel, Tabs, Spacer, Div, Dropdown
from casagui.toolbox import CubeMask, AppContext, RegionList
from casagui.bokeh.utils import svg_icon
from bokeh.io import curdoc
from bokeh.io import reset_output as reset_bokeh_output
from bokeh.models.dom import HTML
from bokeh.models.ui.tooltips import Tooltip
from ..utils import resource_manager, reset_resource_manager, is_notebook
from ..data import casaimage
from ..bokeh.models import TipButton, Tip
from ..utils import ContextMgrChain as CMC

class CreateRegion:
    '''Class that can be used to launch a createregion GUI with ``CreateRegion('test.im')( )``.
    ``CreateRegion`` is implemented with the same libraries that are used to implement
    ``InteractiveClean`` and ``CreateMask``. Regions drawn on the displalyed CASA image
    and then returned as astropy regions.
    '''

    def __stop( self, result ):
        self._drawn_regions = result
        if not self.__result_future.done( ):
            self.__result_future.set_result(self._drawn_regions)

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

        self._image = None
        ###
        ### error or exception result
        ###
        self._error_result = None

    def __expand_mask_paths( self, path_pairs ):
        '''return expanded mask paths

        Parameters
        ----------
        path_pairs: list of tuples
            each tuple contains a string in the first element that represents an image path
            and the second element is either a None which signals that the an mask path should
            be generated based upon the image path or a string which represents that mask path
            for the first element image.

        Returns
        -------
        [ (str,str) ]
            A list of tuples is returned. The first element of each
            tuple is a string that represents the image path and the second element is a string
            which represents the mask path.
        '''
        uniquified_names = { }        ### dict to keep track of repeated iamges

        def create_mask_path( impath ):
            if impath in uniquified_names and uniquified_names[impath][0] > 1:
                uniq = "%032d" % uniquified_names[impath][1]
                uniquified_names[impath][1] += 1
            else:
                uniq = ''
            path,file = splitpath(impath)
            if len(path) > 0 and not exists(path):
                raise RuntimeError( f'''CreateRegion: mask path '{path}' does not exist''' )
            basename,ext = splitext(file)
            return join( path, f'''{basename}{uniq}.mask''')

        ### python zip etc can only be read once
        path_pairs_ = list(path_pairs)
        for p in path_pairs_:
            if p[0] in uniquified_names:
                uniquified_names[p[0]][0] += 1
            else:
                uniquified_names[p[0]] = [1,1]

        return list( map( lambda p: p if p[1] is not None else (p[0],create_mask_path(p[0])), path_pairs_ ) )

    def __create_masks( self, paths ):
        '''Create missing masks...'''
        ### Create any mask images which do not exist (if create=True)
        return list( map( lambda p: (p[0],casaimage.new(*p)) if not exists(p[1]) else p, paths ) )


    def __init__( self, image ):
        '''create a ``createregion`` object which will display image planes from a CASA
        image and allow the user to draw masks for each channel.

        Parameters
        ----------
        image: str or list of str
            path(s) to CASA image for which interactive regions will be drawn
        '''

        ###
        ### Create application context (which includes a temporary directory).
        ### This sets the title of the plot.
        ###
        self._app_state = AppContext( 'Create Region' )

        ###
        ### widgets shared across image tabs (masking multiple images)
        ###
        self._cube_palette = None
        self._image_region_controls = None

        ###
        ### With Bokeh 3.2.2, the spectrum and convergence plots extend beyond the edge of the
        ### browser window (requiring scrolling) if a width is not specified. It could be that
        ### this should be computed from the width of the tabbed control area at the right of
        ### the image display.
        ###
        self._spect_plot_width = 450

        ###
        ### Validate image paths
        ###
        if isinstance(image, str):
            image_paths = [ image ]
        elif isinstance(image, list) and all(isinstance(x, str) for x in image):
            image_paths = image
        else:
            raise RuntimeError( 'CreateRegion: image parameter should be a string or a list of strings' )

        if len(image_paths) == 0:
            raise RuntimeError( 'CreateRegion: at least one image path must be specified' )

        for img in image_paths:
            if not exists(img):
                raise RuntimeError(f'''CreateRegion: image path '{img}' does not exist''')

        self._drawn_regions = { k: [] for k in image_paths }
        self._fig = { 'help': None, 'status': None }
        self._region_state = { }
        self._ctrl_state = { }
        initialization_registered = False
        for path in image_paths:
            _,name = splitpath(path)
            imdetails = self._region_state[name] = { 'gui': { 'image': {}, 'fig': {},
                                                            'image-adjust': { } } }

            ###
            ### Use CubeMask init_script to set up a 'beforeunload' handler which will signal to
            ### CubeMask that the app is shuting down (with 'document._cube_done( )'). It should then
            ### send the final results to Python and then call the provided callback (the Promise
            ### resolve function).
            ###
            ### Waiting for this to complete before the browser tab is unloaded requires waiting
            ### for the promise to be resolved within an async function. Creating one to do the
            ### await works. The promise is resolved when the 'done' function call the Promise's
            ### resolve function which is provide to 'done' as its callback function.
            ###
            ### If debugging this, make only a small change before confirming that exit from the
            ### Python asyncio loop continues to work... seems to be fiddly
            ###
            imdetails['gui']['cube'] = CubeMask( path )

            initialization_registered = True
            imdetails['image-channels'] = imdetails['gui']['cube'].shape( )[3]


            imdetails['gui']['image']['src'] = imdetails['gui']['cube'].js_obj( )
            imdetails['gui']['image']['fig'] = imdetails['gui']['cube'].image( grid=False, height_policy='max', width_policy='max', maxanno=5 )

            if self._fig['help'] is None:
                 self._fig['help'] = self._ctrl_state['help'] = imdetails['gui']['cube'].help( rows=[ '<tr><td><i>stop button</i></td><td>clicking the stop button will close the dialog and control to python</td></tr>' ],
                                                                                 position='right' )
            imdetails['gui']['channel-ctrl'] = imdetails['gui']['cube'].channel_ctrl( )
            imdetails['gui']['cursor-pixel-text'] = imdetails['gui']['cube'].pixel_tracking_text( margin=(-3, 5, 3, 30) )

            self._fig['status'] = imdetails['gui']['status'] = imdetails['gui']['cube'].status_text( "<p>initialization</p>" , width=230, reuse=self._fig['status'] )

            ###
            ### spectrum plot must be disabled during iteration due to "tap to change channel" functionality
            ###
            if imdetails['image-channels'] > 1:
                imdetails['gui']['spectrum'] = imdetails['gui']['cube'].spectrum( orient='vertical', sizing_mode='stretch_height', width=self._spect_plot_width )
                imdetails['gui']['slider'] = imdetails['gui']['cube'].slider( show_value=False, title='', margin=(14,5,5,5), sizing_mode="scale_width" )
                imdetails['gui']['goto'] = imdetails['gui']['cube'].goto( )
            else:
                imdetails['gui']['spectrum'] = None
                imdetails['gui']['slider'] = None
                imdetails['gui']['goto'] = None

        init_args = { 'sources': { } }
        last_cube = None
        for k,v in self._region_state.items( ):
            init_args['sources'][k] = v['gui']['image']['src']
            last_cube = v['gui']['cube']

        def create_close_code( callback='' ):
            CUBE_CALLBACK = f''', {callback}''' if callback else ''
            return f'''let source = null
                       const result = {{ }}
                       const srcmap = casalib.reduce( ( acc, img, src ) => {{
                           result[img] = {{ }}
                           acc[src.id] = img
                           if ( source == null ) source = src
                           return acc }}, sources, {{ }} )
                       if ( source && document._cube_done )
                       document._cube_done(
                           casalib.reduce(
                               (acc, poly) => {{
                                   acc[srcmap[poly.source.id]][poly.label] = {{
                                       channels: poly.getchans( ),
                                   geometry: poly.geometry,
                                   styling: poly.styling }}
                                   return acc }},
                               source._polys.list( ),
                               result )
                           {CUBE_CALLBACK} )'''

        ##
        ## Previously this beforeunload setup was accomplished by adding this to one of the
        ## CubeMask.init_script. This worked until a reference was needed to all of the
        ## ImageDataSources (which is an element of CubeMask). This resulted in a circular
        ## reference when the plot was being rendered.
        ##
        ## The document._cube_done callback ( `(msg) => { resolve(true); return false }` ) can
        ## return `false` (indicating that the window should not be closed by _cube_done)
        ## because the window is already being closed when this beforeunload callback
        ## is called.
        ##
        curdoc( ).js_on_event( 'document_ready', CustomJS( args=init_args,
                                                           code=f'''window.addEventListener( 'beforeunload',
                                                                                             (event) => {{
                                                                                                 function donePromise( ) {{
                                                                                                     return new Promise(
                                                                                                         (resolve,reject) => {{
                                                                                                             {create_close_code('(msg) => { resolve(true); return false }')}
                                                                                                         }} )
                                                                                                 }}
                                                                                                 ( async () => {{ await donePromise( ) }} )( )
                                                                                             }} )''' ) )

        self._ctrl_state['stop'] = TipButton( button_type="danger", max_width=64, max_height=40, name='stop',
                                              icon=svg_icon(icon_name="iclean-stop", size=18),
                                              tooltip=Tooltip( content=HTML( '''Clicking this button will cause this tab to close and control will return to Python.''' ),
                                                                             position='left' ) )

        self._ctrl_state['stop'].js_on_click( CustomJS( args=init_args,
                                                        code=f'''if ( confirm( "Are you sure you want to end this mask creation session and close the GUI?" ) ) {{
                                                                     {create_close_code( )}
                                                                 }}''' ) )

        ###
        ### This is used to tell whether the websockets have been initialized, but also to
        ### indicate if __call__ is being called multiple times to allow for resetting Bokeh
        ###
        self.__initialized = False

        ###
        ### the asyncio future that is used to transmit the result from region creation
        ###
        self.__result_future = None

    def _create_style_adjust( self, imdetails ):

        if 'region-styling' not in imdetails['gui']:
            ### also used in self._create_location_panel
            self._image_region_controls = imdetails['gui']['region-styling'] = imdetails['gui']['cube'].region_style_ctrl( reuse=self._image_region_controls, button_type='light' )

        hover = row( column( Div(text='<div>Fill</div>'),
                             row(*imdetails['gui']['region-styling']['hover']['fill']),
                             Div(text='<div>Line</div>'),
                             row(*imdetails['gui']['region-styling']['hover']['line']) ) )
        hover.styles = {"border": "1px solid black", "padding": "1px" }
        default = row( column( Div(text='<div>Fill</div>'),
                               row(*imdetails['gui']['region-styling']['default']['fill']),
                               Div(text='<div>Line</div>'),
                               row(*imdetails['gui']['region-styling']['default']['line']) ) )
        default.styles = { "border": "1px solid black", "padding": "1px" }
        return column( Div(text='<div><b>Styling for Region with Focus</b></div>'),
                       hover,
                       Div(text='<div><b>Default Style for New Regions</b></div>'),
                       default )

    def _create_location_panel( self, imdetails, width=410 ):
        pos = imdetails['gui']['cube'].region_position_ctrl( )
        coords = grid( [ [ None, Div(text='<b>X</b>'), Div(text='<b>Y</b>') ],
                         [ Div(text='<b>pixel</b>'), *pos['pixel'] ],
                         [ Div(text='<b>world</b>'), *pos['world'] ] ] )
        coord_section = row( column( Div(text='<b>Region Placement</b>'),
                                     coords ),
                             width=width )
        chan_section = row( column( Div(text='<b>Channels</b>'),
                                    *[ row( Div(text=f'''<b>{s}</b>'''), text, sizing_mode='stretch_width' ) for s,text in pos['chan'].items( ) ],
                                    sizing_mode='stretch_width' ),
                            width=width )

        coord_section.styles = {"border": "1px solid black", "padding": "1px" }
        chan_section.styles = {"border": "1px solid black", "padding": "1px" }

        tracking = column( Div(text='<b>Tracking</b>', styles={"margin-top": "10px"} ), row( *pos['tracking'] ), sizing_mode='stretch_width' )
        tracking.styles = {"border": "1px solid black", "padding": "1px" }

        if 'region-styling' not in imdetails['gui']:
            ### also used in self._create_style_adjust
            self._image_region_controls = imdetails['gui']['region-styling'] = imdetails['gui']['cube'].region_style_ctrl( reuse=self._image_region_controls, button_type='light' )

        style = row( column( Div(text='<div>Fill</div>'),
                             row(*imdetails['gui']['region-styling']['selected']['fill']),
                             Div(text='<div>Line</div>'),
                             row(*imdetails['gui']['region-styling']['selected']['line']) ) )
        style.styles = {"border": "1px solid black", "padding": "1px" }

        return column( coord_section,
                       chan_section,
                       row( pos['status'] ),
                       row( column( pos['label'],
                                    tracking, width=140 ),
                            Spacer(width=4),
                            style ) )

    def _create_colormap_adjust( self, imdetails ):
        palette = imdetails['gui']['cube'].palette( reuse=self._cube_palette )
        return column( row( Div(text="<div><b>Colormap:</b></div>",margin=(5,2,5,25)), palette ),
                       imdetails['gui']['cube'].colormap_adjust( ), sizing_mode='stretch_both' )


    def _create_control_image_tab( self, imid, imdetails ):
        result = Tabs( tabs= [ TabPanel( child=self._create_location_panel(imdetails),
                                           title='Placement' ),
                                 TabPanel( child=self._create_style_adjust(imdetails),
                                           title='Config' ) ] +
                             ( [ TabPanel( child=imdetails['gui']['spectrum'],
                                           title='Spectrum' ) ] if imdetails['image-channels'] > 1 else [ ] ) +
                             [ TabPanel( child=self._create_colormap_adjust(imdetails),
                                         title='Colormap' ),
                               TabPanel( child=imdetails['gui']['cube'].statistics( ),
                                         title='Statistics' ) ],
                       width=500, sizing_mode='stretch_height', tabs_location='below' )

        if not hasattr(self,'_image_control_tab_groups'):
            self._image_control_tab_groups = { }

        self._image_control_tab_groups[imid] = result
        result.js_on_change( 'active', CustomJS( args=dict( ),
                                                 code='''document._casa_last_control_tab = cb_obj.active''' ) )
        return result

    def _create_image_panel( self, imagetuple ):
        imid, imdetails = imagetuple

        return TabPanel( child=column( row( *imdetails['gui']['channel-ctrl'], imdetails['gui']['cube'].coord_ctrl( ),
                                            ##Spacer( height=5, height_policy="fixed", sizing_mode="scale_width" ),
                                            imdetails['gui']['cursor-pixel-text'],
                                            row( Spacer( sizing_mode='stretch_width' ),
                                                 imdetails['gui']['cube'].tapedeck( size='20px' ) if imdetails['image-channels'] > 1 else Div( ),
                                                 Spacer( height=5, width=350 ), width_policy='max' ),
                                            width_policy='max' ),
                                       row( imdetails['gui']['image']['fig'],
                                            column( row( imdetails['gui']['goto'],
                                                         imdetails['gui']['slider'],
                                                         width_policy='max' ) if imdetails['image-channels'] > 1 else Div( ),
                                                    self._create_control_image_tab(imid, imdetails), height_policy='max' ),
                                            height_policy='max', width_policy='max' ),
                                       height_policy='max', width_policy='max' ), title=imid )

    def _launch_gui( self ):
        '''create and show GUI
        '''
        self.__initialized = True

        width = 35
        height = 35

        tab_panels = list( map( self._create_image_panel, self._region_state.items( ) ) )

        for imid, imdetails in self._region_state.items( ):
            imdetails['gui']['cube'].connect( )

        image_tabs = Tabs( tabs=tab_panels, tabs_location='below', height_policy='max', width_policy='max' )

        self._fig['layout'] = column(
                                  row( self._fig['help'],
                                       Spacer( height=self._ctrl_state['stop'].height, sizing_mode="scale_width" ),
                                       Div( text="<div><b>status:</b></div>" ),
                                       self._fig['status'],
                                       self._ctrl_state['stop'], sizing_mode="scale_width" ),
                                  row( image_tabs, height_policy='max', width_policy='max' ),
                                  height_policy='max', width_policy='max' )

        ###
        ### Keep track of which image is currently active in document._casa_image_name (which is
        ### initialized in self._js['initialize']). Also, update the current control sub-tab
        ### when the field main-tab is changed. An attempt to manage this all within the
        ### control sub-tabs using a reference to self._image_control_tab_groups from
        ### each control sub-tab failed with:
        ###
        ###     bokeh.core.serialization.SerializationError: circular reference
        ###
        image_tabs.js_on_change( 'active', CustomJS( args=dict( names=[ t[0] for t in self._region_state.items( ) ],
                                                                itergroups=self._image_control_tab_groups ),
                                                     code='''if ( ! hasprop(document,'_casa_last_control_tab') ) {
                                                                 document._casa_last_control_tab = 0
                                                             }
                                                             document._casa_image_name = names[cb_obj.active]
                                                             itergroups[document._casa_image_name].active = document._casa_last_control_tab''' ) )

        # Change display type depending on runtime environment
        if is_notebook( ):
            output_notebook()
        else:
            ### Directory is created when an HTTP server is running
            ### (MAX)
###         output_file(self._imagename+'_webpage/index.html')
            pass

        show(self._fig['layout'])

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
                await s
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

        async with CMC( *( [ ctx for img in self._region_state.keys( ) for ctx in
                             [
                                 self._region_state[img]['gui']['cube'].serve(self.__stop),
                             ]
                           ] ) ):
            self.__result_future = asyncio.Future( )
            yield self.__result_future
        ###async with self._cube.serve( self.__stop ) as cube:
        ###    self.__result_future = asyncio.Future( )
        ###    yield ( self.__result_future, { 'cube': cube } )

    def result( self ):
        '''If InteractiveClean had a return value, it would be filled in as part of the
        GUI dialog between Python and JavaScript and this function would return it'''
        if self.__result_future is None:
            raise RuntimeError( 'no interactive clean result is available' )
        if not self.__result_future.done( ):
            raise RuntimeError( 'regions not yet available to be returned' )

        result = { }
        for img, regions in self.__result_future.result( ).items( ):
            _, fits_header = self._region_state[img]['gui']['cube'].fits_header( )
            result[img] = RegionList( regions, fits_header )

        return result
