from casagui.bokeh.state import initialize_bokeh
#initialize_bokeh( "casaguijs/dist/casaguijs.min.js" )        ### local build
initialize_bokeh( )                                           ### fetch from https://casa.nrao.edu/

import time
import asyncio
import websockets
from uuid import uuid4
from casatasks import imstat
from casagui.utils import find_ws_address
from bokeh.layouts import column, row, Spacer
from bokeh.events import SelectionGeometry
from bokeh.plotting import ColumnDataSource, figure, show
from bokeh.models import CustomJS, TextInput, MultiChoice
from bokeh.models import HoverTool, Range1d, LinearAxis, Span, BoxAnnotation, TableColumn, DataTable
from casagui.bokeh.sources import ImageDataSource, SpectraDataSource, ImagePipe, DataPipe
from bokeh.models import Slider, Button
from bokeh.core.has_props import HasProps
from bokeh.colors import HSL, RGB
from bokeh.colors import Color
from casagui.bokeh.components.custom_icon.svg_icon import SVGIcon

from ._gclean import gclean as _gclean

class iclean:
    '''iclean(...) implements interactive clean it depends on asyncio
    '''
    def __stop( self ):
        if self._image_server is not None and self._image_server.ws_server.loop.is_running( ):
            self._image_server.ws_server.loop.stop( )
        if self._data_server is not None and self._data_server.ws_server.loop.is_running( ):
            self._data_server.ws_server.loop.stop( )

    def __init__( self, vis, imagename, imsize=[100], cell="1arcsec", specmode='cube', nchan=-1, start='',
                  width='', interpolation='linear', gridder='standard', pblimit=0.2, deconvolver='hogbom',
                  niter=0, threshold='0.1Jy', cycleniter=-1, cyclefactor=1.0, scales=[] ):
        ###
        ### used by data pipe (websocket) initialization function
        ###
        self.__pipes_initialized = False

        ###
        ### clean generator
        ###
        self._clean = _gclean( vis=vis, imagename=imagename, imsize=imsize, cell=cell, specmode=specmode,
                               nchan=nchan, start=start, width=width, interpolation=interpolation,
                               gridder=gridder, pblimit=pblimit, deconvolver=deconvolver, niter=niter,
                               threshold=threshold, cycleniter=cycleniter, cyclefactor=cyclefactor,
                               scales=scales )
        self._convergence_rec = next(self._clean)
        ###
        ### Initial Conditions
        ###
        self._params = { }
        self._params['niter'] = niter
        self._params['cycleniter'] = cycleniter
        self._params['threshold'] = threshold
        self._params['cyclefactor'] = cyclefactor
        ###
        ### GUI components
        ###
        self._image_path = "%s.image" % imagename
        self._pipe = { 'data': None, 'image': None }
        self._image_source = None
        self._image_spectra = None
        self._hover = None
        self._cb = { }
        self._ids = { }
        self._fig = { }

        self._image_server = None
        self._data_server = None

        self._mode = 'interactive'         # interactive  =>  perform one step and wait for user
                                           # finish       =>  perform step, update GUI, repeat
                                           #                  until user presses stop or stop
                                           #                  conditions reached

    def __build_data(self, data):
        """
        This function takes in the data array that defines containing the residual and total flu information
        and builds a convenient dictionary array.

        Example:
            The ``data`` array comes as a retuen value of the tclean process::

                $ data = tclean( .... )
                $ __build_data(data)

        Attributes:
            data (numpy.ndarray): Contains data for iteration, residual, total flux, channel.

        Todo:
            * Add support for other array indexs that aren't currenlty used as well as polarization.
            * You have to also use ``sphinx.ext.todo`` extension
        """
        chan = data[5,:]
        iteration = data[0,:]
        residual = data[1,:]
        flux = data[2,:]

        data_dict = []
        for i in range(int(chan.max())):
            data_dict.append({
                'iteration':iteration[chan==i],
                'residual':residual[chan==i],
                'flux':flux[chan==i]
                })

        return data_dict

    def _init_pipes( self ):
        if not self.__pipes_initialized:
            self.__pipes_initialized = True
            self._pipe['data'] = DataPipe(address=find_ws_address( ))
            self._pipe['image'] = ImagePipe(image=self._image_path, address=find_ws_address( ))

    def _launch_gui( self ):

        self._init_pipes( )
        self._image_source = ImageDataSource(image_source=self._pipe['image'])

        self._image_spectra = SpectraDataSource(image_source=self._pipe['image'])
        self._cb['pos'] = CustomJS( args=dict(spectra=self._image_spectra),
                                    code = """var geometry = cb_data['geometry'];
                                              var x_pos = Math.floor(geometry.x);
                                              var y_pos = Math.floor(geometry.y);
                                              spectra.spectra(x_pos,y_pos)
                                           """ )
        self._hover = HoverTool( callback=self._cb['pos'] )
        self._fig['spectra'] = figure( plot_height=200, plot_width=650,
                                       title=None, tools=[] )
        self._fig['spectra'].x_range.range_padding = self._fig['spectra'].y_range.range_padding = 0
        self._fig['spectra'].line( x='x', y='y', source=self._image_spectra )
        self._fig['spectra'].grid.grid_line_width = 0.5

        major = self._convergence_rec['summarymajor']
        minor = self._convergence_rec['summaryminor']

        minor_converge_dict = self.__build_data(minor)
        self._convergence_source = ColumnDataSource(data=minor_converge_dict[0])
        major_convergence_dict = [{ 'iteration': major }]
        self._fig['convergence'] = figure( tooltips=[ ("x","$x"), ("y","$y"), ("value", "@image")],
                                           output_backend="webgl",
                                           tools=["box_select", "pan,wheel_zoom","box_zoom","save","reset","help"],
                                           title='Convergence', x_axis_label='Iteration', y_axis_label='Peak Residual' )
        self._fig['convergence'].extra_y_ranges = { 'flux': Range1d( self._convergence_source.data['flux'].min()*0.5,
                                                                     self._convergence_source.data['flux'].max()*1.5 ) }
        self._fig['convergence'].add_layout( LinearAxis( y_range_name='flux', axis_label='Total Flux' ), 'right' )

        for i in major:
            major_cycle = Span( location=i,
                                dimension='height',
                                line_color='slategray',
                                line_dash='dashed',
                                line_width=2 )
            self._fig['convergence'].add_layout( major_cycle )

        self._fig['convergence'].circle( x='iteration',
                                         y='residual',
                                         color='crimson',
                                         size=10,
                                         alpha=0.4,
                                         legend_label='Peak Residual',
                                         source=self._convergence_source )
        self._fig['convergence'].circle( x='iteration',
                                         y='flux',
                                         color='forestgreen',
                                         size=10,
                                         alpha=0.4,
                                         y_range_name='flux',
                                         legend_label='Total Flux',
                                         source=self._convergence_source )
        self._fig['convergence'].line( x='iteration',
                                       y='residual',
                                       color='crimson',
                                       source=self._convergence_source )

        self._fig['convergence'].line( x='iteration',
                                       y='flux',
                                       color='forestgreen',
                                       y_range_name='flux',
                                       source=self._convergence_source )

        self._fig['convergence'].plot_height = 650
        self._fig['convergence'].plot_width = 650

        self._fig['image'] = figure( tooltips=[("x","$x"), ("y","$y"), ("value", "@d")],
                                     output_backend="webgl",
                                     tools=["box_select","pan,wheel_zoom","box_zoom",self._hover,"save","reset","help"] )

        self._fig['image'].x_range.range_padding = self._fig['image'].y_range.range_padding = 0

        shape = self._pipe['image'].shape()
        self._fig['image'].image( image="d", x=0, y=0,
                                  dw=shape[0], dh=shape[1],
                                  palette="Spectral11",
                                  level="image", source=self._image_source )

        self._fig['image'].grid.grid_line_width = 0.5
        self._fig['image'].plot_height = 600
        self._fig['image'].plot_width = 600

        self._control = { }
        self._control['box'] = BoxAnnotation( left=0, right=0, bottom=0, top=0,
                                              fill_alpha=0.1, line_color='black', fill_color='black' )

        jscode = """
                     box[%r] = cb_obj.start
                     box[%r] = cb_obj.end
        """

        # TClean Controls
        cwidth = 80
        cheight = 50
        self._control['clean'] = { }
        self._control['clean']['continue'] = ( Button( label="", max_width=cwidth, max_height=cheight, name='continue',
                                                       icon=SVGIcon(icon_name="iclean-continue", size=3) ),
                                               Button( label="", max_width=cwidth, max_height=cheight,
                                                       icon=SVGIcon(icon_name="iclean-disabled", size=3) ),
                                               Button( label="", button_type='danger', max_width=cwidth, max_height=cheight,
                                                       icon=SVGIcon(icon_name="iclean-dead", size=3) ) )
        self._control['clean']['finish'] = ( Button( label="", max_width=cwidth, max_height=cheight, name='finish',
                                                     icon=SVGIcon(icon_name="iclean-finish", size=3) ),
                                             Button( label="", max_width=cwidth, max_height=cheight,
                                                     icon=SVGIcon(icon_name="iclean-disabled", size=3) ),
                                             Button( label="", button_type='danger', max_width=cwidth, max_height=cheight,
                                                     icon=SVGIcon(icon_name="iclean-dead", size=3) ) )
        self._control['clean']['stop'] = ( Button( label="", button_type="danger", max_width=cwidth, max_height=cheight, name='stop',
                                                   icon=SVGIcon(icon_name="iclean-stop", size=3) ),
                                           Button( label="", button_type="danger", max_width=cwidth, max_height=cheight,
                                                   icon=SVGIcon(icon_name="iclean-disabled", size=3) ),
                                           Button( label="", button_type='danger', max_width=cwidth, max_height=cheight,
                                                   icon=SVGIcon(icon_name="iclean-dead", size=3) ) )

        self._control['iter'] = TextInput( title="Iterations", value="%s" % self._params['niter'], width=90 )
        self._control['cycleniter'] = TextInput( title="Cycles", value="%s" % self._params['cycleniter'], width=90 )
        self._control['threshold'] = TextInput( title="Threshold", value="%s" % self._params['threshold'], width=90 )
        self._control['cycle_factor'] = TextInput( value="%s" % self._params['cyclefactor'], title="Cycle factor", width=90 )

        async def eh_interactive_continue( msg, self=self ):
            self._clean.update(msg['value'])
            result = await self._clean.__anext__( )
            return dict( action="continue", mode=self._mode, update=dict(state="update",convergence=result) )

        async def eh_interactive_stop( msg, self=self ):
            self.__stop( )
            return dict( action="stop", mode=self._mode, update=dict(state="update", convergence={ }) )

        async def eh_stub( msg, self=self ):
            print(">>>>>>>> in stub %s" % msg)
            return dict( update=dict(state="update",convergence={ }) )

        self._events = { }
        self._events['interactive'] = { }
        self._events['interactive']['continue'] = eh_interactive_continue
        self._events['interactive']['stop'] = eh_interactive_stop
        self._events['interactive']['finish'] = eh_stub

        self._ids['clean'] = { }
        for btn in "continue", 'finish', 'stop':
            async def handle_event( msg, name=btn, id=id, self=self ):
                if msg['action'] == 'continue':
                    self._clean.update(msg['value'])
                    result = await self._clean.__anext__( )
                    return dict( id=id, action=name, update=dict(state="update",convergence=result) )

            self._ids['clean'][btn] = str(uuid4( ))
            print("%s: %s" % ( btn, self._ids['clean'][btn] ) )
            self._pipe['data'].register( self._ids['clean'][btn], self._events['interactive'][btn] )
            self._control['clean'][btn][1].visible = False
            self._control['clean'][btn][2].visible = False
            self._control['clean'][btn][1].disabled = True


        self._cb['clean'] = CustomJS( args=dict( btns=self._control['clean'],
                                                 pipe=self._pipe['data'], ids=self._ids['clean'],
                                                 img_src=self._image_source, spec_src=self._image_spectra,
                                                 niter=self._control['iter'], cycleniter=self._control['cycleniter'],
                                                 threshold=self._control['threshold'], cyclefactor=self._control['cycle_factor']
                                                ),
                                      code='''function update_gui( msg ) {
                                                  if ( msg.action !== 'stop' ) {
                                                      img_src.refresh( )
                                                      spec_src.refresh( )
                                                      for ( let f of [ "continue", "finish", "stop" ] ) {
                                                          btns[f][0].visible = true;
                                                          btns[f][1].visible = false;
                                                      }
                                                  } else {
                                                      for ( let f of [ "continue", "finish", "stop" ] ) {
                                                          btns[f][0].visible = false;
                                                          btns[f][1].visible = false;
                                                          btns[f][2].visible = true;
                                                      }
                                                  }
                                              }
                                              console.log('source',this.origin.name)
                                              if ( btns['continue'][0].visible ) {
                                                  for ( let f of [ "continue", "finish", "stop" ] ) {
                                                      btns[f][0].visible = false;
                                                      btns[f][1].visible = true;
                                                  }
                                                  // only send message for button that was pressed
                                                  // it's unclear whether 'this.origin.' or 'cb_obj.origin.' should be used
                                                  // (or even if 'XXX.origin.' is public)...
                                                  pipe.send( ids[this.origin.name],
                                                             { action: this.origin.name,
                                                               value: { niter: niter.value, cycleniter: cycleniter.value,
                                                                        threshold: threshold.value, cyclefactor: cyclefactor.value } },
                                                             update_gui )
                                              }''' )

        self._control['clean']['continue'][0].js_on_click( self._cb['clean'] )
        self._control['clean']['stop'][0].js_on_click( self._cb['clean'] )

        self._control['imsize'] = TextInput( value="100", title="Imsize", width=120 )

        self._control['cell'] = TextInput( value="8.0arcsec", title="Cell", width=120)

        self._control['specmode'] = TextInput( value="cube", title="Specmode", width=120 )

        self._control['start'] = TextInput( value="1.0GHz", title="Start", width=120 )

        self._control['width'] = TextInput( value="0.1GHz", title="Width", width=120 )

        self._control['number_chan'] = TextInput( value="10", title="Number of channels", width=120 )

        OPTIONS = [('I', 'I'), ('Q', 'Q'), ('U', 'U'), ('V', 'V')]
        self._control['stokes'] = MultiChoice( value=["I"], title="Stokes", options=OPTIONS, width=360 )
        self._control['stokes'].disabled = True   ### enable when switching stokes axes is working

        self._control['deconvolver'] = TextInput( value="hogbom", title="Deconvolver", width=120 )

        self._control['gain'] = TextInput( value="0.1", title="Gain", width=120 )

        self._coordinates = ColumnDataSource( { 'coordinates': ['x0', 'x1', 'y0', 'y1'],
                                                'values':[0, 0, 0, 0] } )

        columns = [ TableColumn(field="coordinates", title="Coordinates"),
                    TableColumn(field="values", title="Values") ]
        self._mask_table = DataTable( source=self._coordinates, columns=columns, width=380, height=300 )

        image_stats = imstat(imagename=self._image_path)

        stats = ColumnDataSource( { 'statistics': [ 'image', 'npoints', 'sum', 'flux',
                                                    'mean', 'stdev', 'min', 'max', 'rms' ],
                                    'values': [ self._image_path, image_stats['npts'][0], image_stats['sum'][0],
                                                image_stats['flux'][0], image_stats['mean'][0],
                                                image_stats['sigma'][0], image_stats['min'][0],
                                                image_stats['max'][0], image_stats['rms'][0], ] } )

        stats_column = [ TableColumn(field='statistics', title='Statistics'),
                         TableColumn(field='values', title='Values') ]

        stats_table = DataTable(source=stats, columns=stats_column, width=580, height=200)

        self._fig['image'].js_on_event( SelectionGeometry,
                                        CustomJS( args=dict( source=self._image_source, box=self._control['box'], mask=self._coordinates),
                                                  code="""const geometry = cb_obj['geometry'];
                                                          const data = source.data;
                                                          console.log(geometry);

                                                          box['left'] = geometry['x0'];
                                                          box['right'] = geometry['x1'];
                                                          box['top'] = geometry['y0'];
                                                          box['bottom'] = geometry['y1'];

                                                          mask.data['values'][0] = Math.floor(geometry['x0']);
                                                          mask.data['values'][1] = Math.floor(geometry['x1']);
                                                          mask.data['values'][2] = Math.floor(geometry['y0']);
                                                          mask.data['values'][3] = Math.floor(geometry['y1']);

                                                          console.log(mask.data);

                                                          mask.change.emit();
                                                          source.change.emit();
                                                  """ ) )

        self._fig['slider'] = Slider( start=0, end=shape[-1]-1, value=0, step=1,
                                      title="Channel", width=380 )

        callback = CustomJS( args=dict( source=self._image_source, converge_source=self._convergence_source,
                                        minor_converge_dict=minor_converge_dict,
                                        figure=self._fig['convergence'], slider=self._fig['slider'] ),
                             code="""source.channel(slider.value);
                                     converge_source.data = minor_converge_dict[slider.value];

                                     figure.extra_y_ranges['flux'].end = 1.5*Math.max(...converge_source.data['flux'])
                                     figure.extra_y_ranges['flux'].start = 0.5*Math.min(...converge_source.data['flux'])
                                  """ )

        self._fig['slider'].js_on_change( 'value', callback )

        self._control['goto'] = TextInput( title="goto channel", value="0", width=90 )

        gtcb = CustomJS( args=dict( goto=self._control['goto'], slider=self._fig['slider'] ),
                         code="""var v = parseInt(goto.value)
                                 if ( v >= %d && v <= %d ) {
                                     slider.value = v
                                     goto.value = ""
                                 }""" % (0,shape[-1]-1) )
        self._control['goto'].js_on_change( 'value', gtcb )

        self._fig['layout'] = row(
                                   column(
                                           row(
                                                self._control['iter'],
                                                self._control['cycleniter'],
                                                self._control['cycle_factor'],
                                                self._control['threshold'] ),
                                           self._fig['slider'],
                                           row( self._control['goto'],
                                                column( self._control['clean']['continue'][0],
                                                        self._control['clean']['continue'][1],
                                                        self._control['clean']['continue'][2] ),
                                                column( self._control['clean']['finish'][0],
                                                        self._control['clean']['finish'][1],
                                                        self._control['clean']['finish'][2] ),
                                                column( self._control['clean']['stop'][0],
                                                        self._control['clean']['stop'][1],
                                                        self._control['clean']['stop'][2] ) ),
                                           Spacer(width=380, height=15, sizing_mode='scale_width'),
                                           self._control['stokes'],
                                           row(self._control['imsize'], self._control['cell'], self._control['specmode']),
                                           row(self._control['specmode'], self._control['start'], self._control['width']),
                                           row(self._control['deconvolver'], self._control['number_chan'], self._control['gain']),
                                           Spacer(width=380, height=70, sizing_mode='scale_width'),
                                           self._mask_table ),
                                   row(
                                        column(
                                                self._fig['image'],
                                                stats_table ),
                                        column(
                                                self._fig['spectra'],
                                                self._fig['convergence'] ) ) )

        self._fig['image'].add_layout(self._control['box'])
        show(self._fig['layout'])


    def _asyncio_loop( self ):
        async def async_loop( f1, f2 ):
            return await asyncio.gather( f1, f2 )

        self._init_pipes( )
        self._image_server = websockets.serve( self._pipe['image'].process_messages, self._pipe['image'].address[0], self._pipe['image'].address[1] )
        self._data_server = websockets.serve( self._pipe['data'].process_messages, self._pipe['data'].address[0], self._pipe['data'].address[1] )
        return async_loop( self._data_server, self._image_server )

    def show( self ):
        self._launch_gui( )
        return self._asyncio_loop( )
