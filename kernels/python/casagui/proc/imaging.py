from casagui.bokeh.state import initialize_bokeh
#initialize_bokeh( "casaguijs/dist/casaguijs.min.js" )        ### local build
initialize_bokeh( )                                           ### fetch from https://casa.nrao.edu/

import time
import asyncio
import websockets
import shutil
from uuid import uuid4
from casatasks import imstat
from casagui.utils import find_ws_address, static_vars, static_dir
from bokeh.layouts import column, row, Spacer
from bokeh.events import SelectionGeometry, MouseEnter
from bokeh.plotting import ColumnDataSource, figure, show
from bokeh.models import CustomJS, TextInput, MultiChoice, Div
from bokeh.models import HoverTool, Range1d, LinearAxis, Span, BoxAnnotation, PolyAnnotation, TableColumn, DataTable
from casagui.bokeh.sources import ImageDataSource, SpectraDataSource, ImagePipe, DataPipe
from bokeh.models import Slider, Button
from bokeh.core.has_props import HasProps
from bokeh.colors import HSL, RGB
from bokeh.colors import Color
from casagui.bokeh.components.custom_icon.svg_icon import SVGIcon

from ._gclean import gclean as _gclean

class iclean:
    '''iclean(...) implements interactive clean using Bokeh

    This class allows for creation of an Bokeh based GUI for iterative, interactive execution of
    ``tclean``. It allows for drawing the mask that will be used by ``tclean`` as well as running
    and stoping clean cycles.

    Example:
        First the interactive clean GUI is created with::

            ic = iclean( vis='refim_point_withline.ms', imagename='test', imsize=512,
                         cell='12.0arcsec', specmode='cube', interpolation='nearest', ... )

        then the GUI is started using an ``asyncio`` event loop::

            asyncio.get_event_loop().run_until_complete(ic.show( ))
            asyncio.get_event_loop().run_forever()

    The GUI will be displayed in a web browser and control will return to Python when the
    user clicks the ``STOP`` button on the GUI. When the ``STOP`` button is colored *red*,
    it means that clicking it will close the tab and return control to Python. When it is
    colored *orange* it means that clicking it will stop ``tclean`` at the next stopping
    point.

    Masks can be specified either with a lasso selection tool or with a box selection tool
    in the _image box_. As the cursor moves around the _image box_, the spectrum through the
    image cube beneath the cursor location is displayed in the _spectrum box_. Quickly tapping
    _mouse one_ within the _image box_ will freeze updates of the _spectrum box_ allowing
    a spectrum of interest to be selected.

    Quickly tapping _mouse one_ within the _spectrum box_ cause the image display to update
    to the channel indicated by the vertical line which track with the cursor in the
    _spectrum box_.

    The _convergence box_ plots the _total flux_ and _peak residual_ to give an indication
    of the convergence quailty. A _statistics table_ provides some key image statistics. All
    of these boxes are updated as the clean operation progresses.

    The cleaning interval is determined by the text inputs along the top of the GUI which
    allow the user to set the ``niter``, ``cycleiter``, ``cyclefactor``, and ``threshold``.
    The three buttons ( _run one interval_, _run until stoping criteral is reached_, and
    _stop_) allow the user to control the clean run.

    At the bottom of the GUI, footnotes accumulate which includes the Python calls to
    ``tclean`` that have been made.

    *Please see ``tclean`` documentation for details about the arguments summarized here.*

    Args:
        vis (str, :obj:`list` of :obj:`str`): Name of input visibility file(s). A single path may
            be specified, e.g. "ngc5921.ms", or a list of paths may be specified, e.g.
            ``['ngc5921a.ms','ngc5921b.ms']``.
        imagename (str): Name of the output images (without a suffix).
        imsize (int, :obj:`list` of int): Number of pixels in a image plane, for example ``[350,250]``.
            ``500`` implies ``[500,500]``. The number of pixels must be even and factorizable by 2,3,5,7 only
            due to FFT limitations.
        cell (str, :obj:`list` of str): Cell size, e.g. ``['0.5arcsec,'0.5arcsec']``. ``'1arcsec'`` is
            equivalent to ``['1arcsec','1arcsec']``
        specmode (str): Spectral definition mode (mfs,cube,cubedata, cubesource)
            * mode='mfs' : Continuum imaging with only one output image channel
            * mode='cube' : Spectral line imaging with one or more channels
            * mode='cubedata' : Spectral line imaging with one or more channels
        nchan (int): Number of channels in the output image. For default (=-1),
            the number of channels will be automatically determined based on data
            selected by 'spw' with 'start' and 'width'.
        start (int, str): First channel (e.g. start=3,start='1.1GHz',start='15343km/s'.
        width (int, str): Channel width (e.g. width=2,width='0.1MHz',width='10km/s') of output cube images
            specified by data channel number (integer), velocity (string with a unit), or frequency (string
            with a unit).
        interpolation (str): Spectral interpolation (nearest,linear,cubic). Interpolation
            rules to use when binning data channels onto image channels and evaluating
            visibility values at the centers of image channels.
        gridder (str): Gridding options (standard, wproject, widefield, mosaic, awproject)
        pblimit (float): PB gain level at which to cut off normalizations
        deconvolver (str): Minor cycle algorithm (hogbom,clark,multiscale,mtmfs,mem,clarkstokes)
        niter (int): Maximum total number of iterations
        threshold (str | float): Stopping threshold (number in units of Jy, or string).
        cycleniter (int): Maximum number of minor-cycle iterations (per plane) before triggering a major cycle
        cyclefactor (float): Scaling on PSF sidelobe level to compute the minor-cycle stopping threshold.
        scales (:obj:`list` of int): List of scale sizes (in pixels) for multi-scale algorithms

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
        ###
        ### self._convergence_rec:  raw convergence information as returned by tclean
        ### self._convergence_data: accumulated, pre-channel convergence information
        ###                         used by ColumnDataSource
        ###
        self._convergence_rec = next(self._clean)
        self._convergence_data = { }
        self._convergence_id = str(uuid4( ))

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
        self._imagename = imagename
        self._image_path = "%s.image" % imagename
        self._pipe = { 'data': None, 'image': None }
        self._image_source = None
        self._image_spectra = None
        self._hover = { }
        self._cb = { }
        self._ids = { }
        self._fig = { }
        self._status = { }
        self._last_mask = ''

        self._image_server = None
        self._data_server = None

        self._mode = 'interactive'         # interactive  =>  perform one step and wait for user
                                           # finish       =>  perform step, update GUI, repeat
                                           #                  until user presses stop or stop
                                           #                  conditions reached

    @static_vars( iterDone=0,     peakRes=1,         modelFlux=2,
                  cycleThresh=3,  mapperId=4,        chan=5,
                  pol=6,          cycleStartIters=7, startIterDone=8,
                  startPeakRes=9, startModelFlux=10, startPeakResNM=11,
                  peakResNM=12,   stopCode=13 )
    def __minorsummary( prevdone, data ):
        from casatasks.private.imagerhelpers.imager_base import PySynthesisImager
        summary = PySynthesisImager.indexMinorCycleSummaryBySubimage(data)
        stokes = 0
        return { chan:
                 { s: [ x + prevdone[chan] for x in summary[chan][stokes][getattr(iclean.__minorsummary,s)]]
                      if s == 'iterDone' else summary[chan][stokes][getattr(iclean.__minorsummary,s)]
                   for s in static_dir(iclean.__minorsummary) }
                 for chan in summary.keys() }

    def __update_convergence( self, data ):
        summary = iclean.__minorsummary( [ max(chandata['iteration']) for k,chandata in self._convergence_data.items( ) ], data )
        self._convergence_data = { chan: { s[1]: self._convergence_data[chan][s[1]] + summary[chan][s[0]] for s in [ ('modelFlux','flux'), ('iterDone','iteration'), ('peakRes','residual') ] } for chan in summary }

    def __init_convergence(self, data):
        summary = iclean.__minorsummary( [0] * data.shape[1], data )
        self._convergence_data = { chan: { s[1]: summary[chan][s[0]] for s in [ ('modelFlux','flux'), ('iterDone','iteration'), ('peakRes','residual') ] } for chan in summary }

    def _init_pipes( self ):
        if not self.__pipes_initialized:
            self.__pipes_initialized = True
            self._pipe['data'] = DataPipe(address=find_ws_address( ))
            self._pipe['image'] = ImagePipe(image=self._image_path, stats=True, address=find_ws_address( ))

    def _launch_gui( self ):

        self._init_pipes( )
        self._image_source = ImageDataSource(image_source=self._pipe['image'])

        self._image_spectra = SpectraDataSource(image_source=self._pipe['image'])


        shape = self._pipe['image'].shape()
        self._fig['slider'] = Slider( start=0, end=shape[-1]-1, value=0, step=1,
                                      title="Channel", width=380 )

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
                                              }
                                           """ )
        self._hover['spectra'] = HoverTool( callback=self._cb['sppos'] )

        self._fig['spectra'] = figure( plot_height=180, plot_width=800,
                                       title="Spectrum", tools=[ self._hover['spectra'] ] )
        self._fig['spectra'].add_layout(self._sp_span)

        self._cb['sptap'] = CustomJS( args=dict( span=self._sp_span, slider=self._fig['slider'] ),
                                      code = '''if ( span.location >= 0 ) {
                                                    slider.value = span.location
                                                }''' )
        self._fig['spectra'].js_on_event('tap', self._cb['sptap'])


        self._fig['spectra'].x_range.range_padding = self._fig['spectra'].y_range.range_padding = 0
        self._fig['spectra'].line( x='x', y='y', source=self._image_spectra )
        self._fig['spectra'].grid.grid_line_width = 0.5


        self._cb['impos'] = CustomJS( args=dict( specds=self._image_spectra, specfig=self._fig['spectra'],
                                                 state=dict(frozen=False) ),
                                    code = """if ( cb_obj.event_type === 'move' && state.frozen !== true ) {
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
                                           """ )
        self._hover['image'] = HoverTool( callback=self._cb['impos'], tooltips=None )

        self.__init_convergence( self._convergence_rec['summaryminor'] )
        self._convergence_source = ColumnDataSource(data=self._convergence_data[0])

        self._fig['convergence'] = figure( tooltips=[ ("x","$x"), ("y","$y"), ("value", "@image")],
                                           output_backend="webgl", plot_height=180, plot_width=800,
                                           tools=[ ],
                                           title='Convergence', x_axis_label='Iteration', y_axis_label='Peak Residual' )
        self._fig['convergence'].yaxis.axis_label_text_color = 'crimson'
        self._fig['convergence'].extra_y_ranges = { 'flux': Range1d( min(self._convergence_source.data['flux'])*0.5,
                                                                     max(self._convergence_source.data['flux'])*1.5 ) }
        self._fig['convergence'].add_layout( LinearAxis( y_range_name='flux', axis_label='Total Flux', axis_label_text_color='forestgreen' ), 'right' )

        ###
        ### Bokeh Spans cannot be used because one Span object must be created for each
        ### line on the plot. However, the convergence plot is updated after the browser
        ### display is created, but it is not possible to create new elements after the
        ### browser window is up (we can only update existing elements). We could do the
        ### last N major cycle Spans...
        ###
        #for i in major:
        #    major_cycle = Span( location=i,
        #                        dimension='height',
        #                        line_color='slategray',
        #                        line_dash='dashed',
        #                        line_width=2 )
        #    self._fig['convergence'].add_layout( major_cycle )


        self._fig['convergence'].circle( x='iteration',
                                         y='residual',
                                         color='crimson',
                                         size=10,
                                         alpha=0.4,
                                         #legend_label='Peak Residual',
                                         source=self._convergence_source )
        self._fig['convergence'].circle( x='iteration',
                                         y='flux',
                                         color='forestgreen',
                                         size=10,
                                         alpha=0.4,
                                         y_range_name='flux',
                                         #legend_label='Total Flux',
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

        self._fig['image'] = figure( output_backend="webgl",
                                     tools=[ "lasso_select","box_select","pan,wheel_zoom","box_zoom",self._hover['image'],"save","reset" ],
                                     tooltips=None
                                    )
                                     #tools=["lasso_select","box_select","pan,wheel_zoom","box_zoom",self._hover['image'],"save","reset","help"] )

        self._fig['image'].x_range.range_padding = self._fig['image'].y_range.range_padding = 0

        self._fig['image'].image( image="d", x=0, y=0,
                                  dw=shape[0], dh=shape[1],
                                  palette="Spectral11",
                                  level="image", source=self._image_source )

        self._fig['image'].grid.grid_line_width = 0.5
        self._fig['image'].plot_height = 400
        self._fig['image'].plot_width = 400

        self._fig['image'].js_on_event('mouseenter',self._cb['impos'])
        self._fig['image'].js_on_event('tap',self._cb['impos'])

        self._mask = { }
        self._mask['rect'] = BoxAnnotation( left=0, right=0, bottom=0, top=0,
                                           fill_alpha=0.1, line_color='black', fill_color='black' )
        self._mask['poly'] = PolyAnnotation( xs=[], ys=[],
                                             fill_alpha=0.1, line_color='black', fill_color='black' )

        jscode = """
                     box[%r] = cb_obj.start
                     box[%r] = cb_obj.end
        """

        self._status['log'] = Div( text="<hr><p>%s</p>" % self._clean.cmds( )[-1] )
        self._status['stopcode'] = Div( text="<div>initial image</div>" )

        ### statistics for first image plane
        image_stats = self._pipe['image'].statistics( [0,0] )
        self._stats_source = ColumnDataSource( { 'labels': list(image_stats.keys( )),
                                                 'values': list(image_stats.values( )) } )

        stats_column = [ TableColumn(field='labels', title='Statistics', width=75),
                         TableColumn(field='values', title='Values') ]

        stats_table = DataTable(source=self._stats_source, columns=stats_column, width=400, height=200, autosize_mode='none')

        # TClean Controls
        cwidth = 80
        cheight = 50
        self._control = { }
        self._control['clean'] = { }
        self._control['clean']['continue'] = Button( label="", max_width=cwidth, max_height=cheight, name='continue',
                                                     icon=SVGIcon(icon_name="iclean-continue", size=2.5) )
        self._control['clean']['finish'] = Button( label="", max_width=cwidth, max_height=cheight, name='finish',
                                                   icon=SVGIcon(icon_name="iclean-finish", size=2.5) )
        self._control['clean']['stop'] = Button( label="", button_type="danger", max_width=cwidth, max_height=cheight, name='stop',
                                                 icon=SVGIcon(icon_name="iclean-stop", size=2.5) )

        self._control['iter'] = TextInput( title="iter", value="%s" % self._params['niter'], width=90 )
        self._control['cycleniter'] = TextInput( title="cycleniter", value="%s" % self._params['cycleniter'], width=90 )
        self._control['threshold'] = TextInput( title="threshold", value="%s" % self._params['threshold'], width=90 )
        self._control['cycle_factor'] = TextInput( value="%s" % self._params['cyclefactor'], title="cyclefactor", width=90 )

        def convergence_handler( msg, self=self ):
            if msg['value'] in self._convergence_data:
                return { 'action': 'update-success', 'result': dict(converge=self._convergence_data[msg['value']]) }
            else:
                return { 'action': 'update-failure' }

        self._pipe['data'].register( self._convergence_id, convergence_handler )

        async def clean_handler( msg, self=self ):
            if msg['action'] == 'next':
                if 'mask' in msg['value'] and msg['value']['mask'] != self._last_mask:
                    self._last_mask = msg['value']['mask']
                    mask_dir = "%s.mask" % self._imagename
                    shutil.rmtree(mask_dir)
                else:
                    msg['value']['mask'] = ''
                self._clean.update(msg['value'])
                result = await self._clean.__anext__( )
                stopcode = result['stopcode'] if 'stopcode' in result else 0
                self.__update_convergence(result['summaryminor'])
                return dict( result='update', stopcode=stopcode, cmd="<p>%s</p>" % self._clean.cmds( )[-1] )
            elif msg['action'] == 'stop':
                self.__stop( )
                return dict( result='stopped', update=dict( ) )
            elif msg['action'] == 'status':
                return dict( result="ok", update=dict( ) )
            else:
                print( "got something else: '%s'" % msg['action'] )

        self._ids['clean'] = { }
        for btn in "continue", 'finish', 'stop':
            self._ids['clean'][btn] = str(uuid4( ))
            print("%s: %s" % ( btn, self._ids['clean'][btn] ) )
            self._pipe['data'].register( self._ids['clean'][btn], clean_handler )

        self._cb['clean'] = CustomJS( args=dict( btns=self._control['clean'],
                                                 state=dict( mode='interactive', stopped=False, awaiting_stop=False, mask="" ),
                                                 pipe=self._pipe['data'], ids=self._ids['clean'],
                                                 img_src=self._image_source, spec_src=self._image_spectra,
                                                 niter=self._control['iter'], cycleniter=self._control['cycleniter'],
                                                 threshold=self._control['threshold'], cyclefactor=self._control['cycle_factor'],
                                                 convergence_src=self._convergence_source,
                                                 convergence_id=self._convergence_id, slider=self._fig['slider'],
                                                 convergence_fig=self._fig['convergence'],
                                                 log=self._status['log'], img_fig=self._fig['image'],
                                                 stopstatus=self._status['stopcode'], stat_src=self._stats_source
                                                ),
                                      code='''function refresh( ) {
                                                  function upconv( msg ) {
                                                      if ( 'result' in msg ) {
                                                          convergence_src.data = msg.result.converge
                                                          convergence_fig.extra_y_ranges['flux'].end = 1.5*Math.max(...msg.result.converge['flux'])
                                                          convergence_fig.extra_y_ranges['flux'].start = 0.5*Math.min(...msg.result.converge['flux'])
                                                      }
                                                  }
                                                  img_src.refresh( msg => {
                                                      if ( 'stats' in msg ) {
                                                         stat_src.data = msg.stats
                                                      }
                                                  } )
                                                  spec_src.refresh( )
                                                  pipe.send( convergence_id, { action: 'update', value: slider.value }, upconv )
                                              }
                                              // enabling/disabling tools in self._fig['image'].toolbar.tools does not seem to not work
                                              // self._fig['image'].toolbar.tools.tool_name (e.g. "Box Select", "Lasso Select")
                                              function disable( with_stop ) {
                                                  img_src._mask_disabled = true
                                                  niter.disabled = true
                                                  cycleniter.disabled = true
                                                  threshold.disabled = true
                                                  cyclefactor.disabled = true
                                                  btns['continue'].disabled = true
                                                  btns['finish'].disabled = true
                                                  if ( with_stop ) {
                                                      btns['stop'].disabled = true
                                                  } else {
                                                      btns['stop'].disabled = false
                                                  }
                                              }
                                              function enable( only_stop ) {
                                                  img_src._mask_disabled = false
                                                  niter.disabled = false
                                                  cycleniter.disabled = false
                                                  threshold.disabled = false
                                                  cyclefactor.disabled = false
                                                  niter.disabled = false
                                                  btns['stop'].disabled = false
                                                  if ( ! only_stop ) {
                                                      btns['continue'].disabled = false
                                                      btns['finish'].disabled = false
                                                  }
                                              }
                                              function update_status( status ) {
                                                  const stopstr = [ 'zero stop code',
                                                                     'iteration limit hit',
                                                                     'force stop',
                                                                     'no change in peak residual across two major cycles',
                                                                     'peak residual increased by 3x from last major cycle',
                                                                     'peak residual increased by 3x from the minimum',
                                                                     'zero mask found',
                                                                     'n-sigma or other valid exit criterion',
                                                                     'unrecognized stop code' ]
                                                  if ( typeof status === 'number' ) {
                                                      stopstatus.text = '<div>' +
                                                                            stopstr[ status < 0 || status >= stopstr.length ?
                                                                                     stopstr.length - 1 : status ] +
                                                                            '</div>'
                                                  } else {
                                                      stopstatus.text = `<div>${status}</div>`
                                                  }
                                              }
                                              function update_gui( msg ) {
                                                  if ( msg.result === 'stopped' ) {
                                                      window.close()
                                                  } else if ( msg.result === 'update' ) {
                                                      if ( 'cmd' in msg ) {
                                                         log.text = log.text + msg.cmd
                                                      }
                                                      refresh( )
                                                      state.stopped = state.stopped || msg.stopcode > 1 || msg.stopcode == 0
                                                      if ( state.mode === 'interactive' && ! state.awaiting_stop ) {
                                                          btns['stop'].button_type = "danger"
                                                          update_status( 'stopcode' in msg ? msg.stopcode : -1 )
                                                          if ( ! state.stopped ) {
                                                              enable( false )
                                                          } else {
                                                              disable( false )
                                                          }
                                                      } else if ( state.mode === 'continuous' && ! state.awaiting_stop ) {
                                                          if ( ! state.stopped ) {
                                                              pipe.send( ids[cb_obj.origin.name],
                                                                         { action: 'next',
                                                                           value: { niter: niter.value, cycleniter: cycleniter.value,
                                                                                    threshold: threshold.value, cyclefactor: cyclefactor.value,
                                                                                    mask: '_mask_clean' in img_src ? img_src._mask_clean : '' } },
                                                                         update_gui )
                                                          } else {
                                                              state.mode = 'interactive'
                                                              btns['stop'].button_type = "danger"
                                                              //disable( false )
                                                              enable(false)
                                                              state.stopped = false
                                                              update_status( 'stopcode' in msg ? msg.stopcode : -1 )
                                                          }
                                                      }
                                                  }
                                              }
                                              function wait_for_tclean_stop( msg ) {
                                                  state.mode = 'interactive'
                                                  btns['stop'].button_type = "danger"
                                                  // enable( state.stopped )
                                                  enable( false )
                                                  state.awaiting_stop = false
                                                  refresh( )
                                                  update_status( 'user requested stop' )
                                              }
                                              if ( ! state.stopped && cb_obj.origin.name == 'finish' ) {
                                                  state.mode = 'continuous'
                                                  update_status( 'running multiple iterations' )
                                                  disable( false )
                                                  btns['stop'].button_type = "warning"
                                                  pipe.send( ids[cb_obj.origin.name],
                                                             { action: 'next',
                                                               value: { niter: niter.value, cycleniter: cycleniter.value,
                                                                        threshold: threshold.value, cyclefactor: cyclefactor.value,
                                                                        mask: '_mask_clean' in img_src ? img_src._mask_clean : '' } },
                                                             update_gui )
                                              }
                                              if ( ! state.stopped && state.mode === 'interactive' &&
                                                   cb_obj.origin.name === 'continue' ) {
                                                  update_status( 'running one iteration' )
                                                  disable( true )
                                                  // only send message for button that was pressed
                                                  // it's unclear whether 'this.origin.' or 'cb_obj.origin.' should be used
                                                  // (or even if 'XXX.origin.' is public)...
                                                  pipe.send( ids[cb_obj.origin.name],
                                                             { action: 'next',
                                                               value: { niter: niter.value, cycleniter: cycleniter.value,
                                                                        threshold: threshold.value, cyclefactor: cyclefactor.value,
                                                                        mask: '_mask_clean' in img_src ? img_src._mask_clean : '' } },
                                                             update_gui )
                                              }
                                              if ( state.mode === 'interactive' && cb_obj.origin.name === 'stop' ) {
                                                  disable( true )
                                                  pipe.send( ids[cb_obj.origin.name],
                                                             { action: 'stop',
                                                               value: { } },
                                                             update_gui )
                                              } else if ( state.mode === 'continuous' &&
                                                          cb_obj.origin.name === 'stop' &&
                                                          ! state.awaiting_stop ) {
                                                  disable( true )
                                                  state.awaiting_stop = true
                                                  pipe.send( ids[cb_obj.origin.name],
                                                             { action: 'status',
                                                               value: { } },
                                                             wait_for_tclean_stop )
                                              }''' )

        self._control['clean']['continue'].js_on_click( self._cb['clean'] )
        self._control['clean']['finish'].js_on_click( self._cb['clean'] )
        self._control['clean']['stop'].js_on_click( self._cb['clean'] )

        OPTIONS = [('I', 'I'), ('Q', 'Q'), ('U', 'U'), ('V', 'V')]
        #self._control['stokes'] = MultiChoice( value=["I"], title="Stokes", options=OPTIONS, width=360 )
        #self._control['stokes'].disabled = True   ### enable when switching stokes axes is working

        self._fig['image'].js_on_event( SelectionGeometry,
                                        CustomJS( args=dict( source=self._image_source,
                                                             box=self._mask['rect'], poly=self._mask['poly'] ),
                                                  code="""if ( source._mask_disabled != true ){
                                                              const geometry = cb_obj['geometry'];
                                                              if ( geometry.type === 'rect' ) {
                                                                  poly.xs = [ ]
                                                                  poly.ys = [ ]
                                                                  box.left = geometry.x0
                                                                  box.right = geometry.x1
                                                                  box.top = geometry.y0
                                                                  box.bottom = geometry.y1
                                                                  // box [ [ 100pix , 130pix] , [120pix, 150pix ] ]
                                                                  source._mask_clean = `box[ [ ${box.left.toFixed(1)}pix, ${box.bottom.toFixed(1)}pix ], [ ${box.right.toFixed(1)}pix, ${box.top.toFixed(1)}pix ] ]`
                                                              } else if ( geometry.type === 'poly' && cb_obj.final ) {
                                                                  box.left = 0
                                                                  box.right = 0
                                                                  box.top = 0
                                                                  box.bottom = 0
                                                                  poly.xs = [ ].slice.call(geometry.x)
                                                                  poly.ys = [ ].slice.call(geometry.y)
                                                                  var coords = poly.xs.map( function(e, i) { return `[ ${e.toFixed(1)}pix, ${poly.ys[i].toFixed(1)}pix ]` } )
                                                                  source._mask_clean = `poly[ ${coords.join(", ")} ]`
                                                              }
                                                          }""" ) )
        self._fig['image'].js_on_event( 'reset',
                                        CustomJS( args=dict( box=self._mask['rect'], poly=self._mask['poly'],
                                                             source=self._image_source ),
                                                  code="""console.log("reset pressed")
                                                          box.left = 0
                                                          box.right = 0
                                                          box.top = 0
                                                          box.bottom = 0
                                                          poly.xs = [ ]
                                                          poly.ys = [ ]
                                                          source._mask_clean = ''""" ) )


        callback = CustomJS( args=dict( source=self._image_source, convergence_src=self._convergence_source,
                                        minor_converge_dict=self._convergence_data,
                                        figure=self._fig['convergence'], slider=self._fig['slider'],
                                        pipe=self._pipe['data'], convergence_id=self._convergence_id,
                                        stat_src=self._stats_source
                                       ),
                             code="""function update_convergence( msg ) {
                                         if ( 'result' in msg ) {
                                             convergence_src.data = msg.result.converge
                                             figure.extra_y_ranges['flux'].end = 1.5*Math.max(...msg.result.converge['flux'])
                                             figure.extra_y_ranges['flux'].start = 0.5*Math.min(...msg.result.converge['flux'])
                                         }
                                     }
                                     source.channel( slider.value, 0,
                                                     msg => { if ( 'stats' in msg ) { stat_src.data = msg.stats } } )
                                     pipe.send( convergence_id,
                                                { action: 'update', value: slider.value },
                                                update_convergence )""" )

        self._fig['slider'].js_on_change( 'value', callback )

        self._control['goto'] = TextInput( title="goto channel", value="", width=90 )

        gtcb = CustomJS( args=dict( goto=self._control['goto'], slider=self._fig['slider'] ),
                         code="""var v = parseInt(goto.value)
                                 if ( v >= %d && v <= %d ) {
                                     slider.value = v
                                     goto.value = ""
                                 }""" % (0,shape[-1]-1) )
        self._control['goto'].js_on_change( 'value', gtcb )

        self._fig['layout'] = column(
                                  row(
                                      column(
                                          row( self._control['iter'],
                                               self._control['cycleniter'],
                                               self._control['cycle_factor'],
                                               self._control['threshold'] ),
                                          self._fig['slider'],
                                          row( self._control['goto'],
                                               self._control['clean']['continue'],
                                               self._control['clean']['finish'],
                                               self._control['clean']['stop'] ),
                                          row ( Div( text="<div><b>status:</b></div>" ), self._status['stopcode'] ),
                                          stats_table ),
                                      self._fig['image'] ),
                                  self._fig['spectra'],
                                  self._fig['convergence'],
                                  Spacer(width=380, height=40, sizing_mode='scale_width'),
                                  self._status['log'] )

        self._fig['image'].add_layout(self._mask['rect'])
        self._fig['image'].add_layout(self._mask['poly'])
        show(self._fig['layout'])


    def _asyncio_loop( self ):
        async def async_loop( f1, f2 ):
            return await asyncio.gather( f1, f2 )

        self._init_pipes( )
        self._image_server = websockets.serve( self._pipe['image'].process_messages, self._pipe['image'].address[0], self._pipe['image'].address[1] )
        self._data_server = websockets.serve( self._pipe['data'].process_messages, self._pipe['data'].address[0], self._pipe['data'].address[1] )
        return async_loop( self._data_server, self._image_server )

    def show( self, runloop=True ):
        '''Launch and display GUI.

        Example:
            Launch and run interactive clean in an event loop:

                ic = iclean( vis='refim_point_withline.ms', imagename='test', imsize=512,
                         cell='12.0arcsec', specmode='cube', interpolation='nearest', ... )
                ic.show( )

            Retrieve event loop to combine with other event based operations:

                ic = iclean( vis='refim_point_withline.ms', imagename='test', imsize=512,
                         cell='12.0arcsec', specmode='cube', interpolation='nearest', ... )
                try:
                    asyncio.get_event_loop().run_until_complete(ic.show(False))
                    asyncio.get_event_loop().run_forever()

                except KeyboardInterrupt:
                    print('\nInterrupt received, shutting down ...')
        '''

        self._launch_gui( )
        if runloop:
            try:
                asyncio.get_event_loop().run_until_complete(self._asyncio_loop( ))
                asyncio.get_event_loop().run_forever()
            except KeyboardInterrupt:
                print('\nInterrupt received, stopping GUI...')
        else:
            return self._asyncio_loop( )