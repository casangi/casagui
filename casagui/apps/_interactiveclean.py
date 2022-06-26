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
'''implementation of the ``InteractiveClean`` application for interactive control
of tclean'''
import copy
import asyncio
import shutil
import websockets
from uuid import uuid4
from bokeh.models import Button, TextInput, Div, Range1d, LinearAxis, CustomJS
from bokeh.plotting import ColumnDataSource, figure, show
from bokeh.layouts import column, row, Spacer
from ..utils import resource_manager

try:
    from casatasks.private.imagerhelpers._gclean import gclean as _gclean
except:
    _gclean = None
    from casagui.utils import warn_import
    warn_import('casatasks')

from casagui.utils import find_ws_address, convert_masks
from casagui.toolbox import CubeMask
from casagui.bokeh.components import SVGIcon
from casagui.bokeh.sources import DataPipe

class InteractiveClean:
    '''InteractiveClean(...) implements interactive clean using Bokeh

    This class allows for creation of an Bokeh based GUI for iterative, interactive execution of
    ``tclean``. It allows for drawing the mask that will be used by ``tclean`` as well as running
    and stoping clean cycles.

    Example:
        First the interactive clean GUI is created with::

            ic = InteractiveClean( vis='refim_point_withline.ms', imagename='test', imsize=512,
                                   cell='12.0arcsec', specmode='cube', interpolation='nearest', ... )

        and then the GUI can be started with::

            ic( )

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

    *Please see tclean documentation for details about the arguments summarized here.*

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
        resource_manager.stop_asyncio_loop()
        if self._control_server is not None and self._control_server.ws_server.is_serving( ):
            resource_manager.stop_asyncio_loop()
        if self._converge_server is not None and self._converge_server.ws_server.is_serving( ):
            resource_manager.stop_asyncio_loop()

    def _abort_handler( self, loop, err ):
        self._error_result = err
        self.__stop( )

    def __init__( self, vis, imagename, imsize=[100], cell="1arcsec", specmode='cube', nchan=-1, start='',
                  width='', interpolation='linear', gridder='standard', pblimit=0.2, deconvolver='hogbom',
                  niter=0, threshold='0.1Jy', cycleniter=-1, cyclefactor=1.0, scales=[] ):

        ###
        ### used by data pipe (websocket) initialization function
        ###
        self.__pipes_initialized = False

        ###
        ### color specs
        ###
        self._color = { 'residual': 'black',
                        'flux':     'forestgreen' }

        ###
        ### clean generator
        ###
        if _gclean is None:
            raise RuntimeError('casatasks gclean interface is not available')

        self._clean = _gclean( vis=vis, imagename=imagename, imsize=imsize, cell=cell, specmode=specmode, nchan=nchan,
                               start=start, width=width, interpolation=interpolation, gridder=gridder, pblimit=pblimit,
                               deconvolver=deconvolver, niter=niter, threshold=threshold, cycleniter=cycleniter,
                               cyclefactor=cyclefactor, scales=scales,
                               history_filter= lambda index, arg, history_value: f'mask=masks[{len(self._mask_history)-1}]' if arg == 'mask' else history_value )
        ###
        ### self._convergence_data: accumulated, pre-channel convergence information
        ###                         used by ColumnDataSource
        ###
        self._status = { }
        stopcode, self._convergence_data = next(self._clean)
        if stopcode > 1 and stopcode < 9: # 1: iteration limit hit, 9: major cycle limit hit
            self._clean.finalize()
        if len(self._convergence_data.keys()) == 0:
            raise RuntimeError("No convergence data for iclean. Did tclean exit without any minor cycles?")
        self._convergence_id = str(uuid4( ))
        #print(f'convergence:',self._convergence_id)

        self._status['log'] = Div( text='''<hr style="width:790px"><p style="width:790px">%s</p>''' % self._clean.cmds( )[-1] )
        self._status['stopcode'] = Div( text="<div>initial image</div>" )

        ###
        ### Initial Conditions
        ###
        self._params = { }
        self._params['niter'] = niter
        self._params['cycleniter'] = cycleniter
        self._params['threshold'] = threshold
        self._params['cyclefactor'] = cyclefactor
        ###
        ### Polarity plane
        ###
        self._stokes = 0

        ###
        ### GUI Elements
        self._imagename = imagename
        self._residual_path = ("%s.residual" % imagename) if self._clean.has_next() else (self._clean.finalize()['image'])
        self._pipe = { 'control': None, 'converge': None }
        self._control = { }
        self._cb = { }
        self._ids = { }
        self._last_mask_breadcrumbs = ''
        self._mask_history = [ ]

        ###
        ### The tclean convergence data is automatically generated by tclean and it
        ### accumulates in this object. If the data becomes bigger than these
        ### thresholds, the implementation switches to fetching threshold data
        ### from python for each channel selected in the GUI within the browser.
        ###
        self._threshold_chan = 400
        self._threshold_iterations = 2000

        self._js = { ### initialize state
                     ### --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
                     ### -- convergence_src is used storing state (initialized and convergence data cache below   --
                     ### --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
                     'initialize':      '''if ( ! convergence_src._initialized ) {
                                               convergence_src._initialized = true
                                               window.addEventListener( 'beforeunload',
                                                                        function (e) {
                                                                            ctrl_pipe.send( ids['stop'],
                                                                                            { action: 'stop', value: { } },
                                                                                              undefined ) }
                                                                      )
                                           }''',

                     ### --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
                     ### -- convergence_src._convergence_data is used to store the complete                       --
                     ### --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
                     'update-converge': '''function update_convergence( msg ) {
                                               if ( typeof msg === 'undefined' && '_convergence_data' in convergence_src ) {
                                                   // use complete convergence cache attached to convergence_src...
                                                   // get the convergence data for channel and stokes
                                                   const pos = img_src.cur_chan
                                                   convergence_src.data = convergence_src._convergence_data[pos[1]][pos[0]]
                                                   //                             chan----------------------^^^^^^  ^^^^^^----stokes
                                               } else if ( 'result' in msg ) {
                                                   // update based on msg received from conv_pipe
                                                   convergence_src.data = msg.result.converge
                                               }
                                               convergence_fig.extra_y_ranges['modelFlux'].end = 1.5*Math.max(...convergence_src.data['modelFlux'])
                                               convergence_fig.extra_y_ranges['modelFlux'].start = 0.5*Math.min(...convergence_src.data['modelFlux'])
                                           }''',

                     'clean-refresh':   '''function refresh( clean_msg ) {
                                               let stokes = 0    // later we will receive the polarity
                                                                 // from some widget mechanism...
                                               //img_src.refresh( msg => { if ( 'stats' in msg ) { //  -- this should happen within CubeMask
                                               //                              stat_src.data = msg.stats
                                               //                          }
                                               //                        } )
                                               img_src.refresh( )
                                               if ( clean_msg !== undefined && 'convergence' in clean_msg ) {
                                                   // save convergence information and update convergence using saved state
                                                   if ( clean_msg.convergence === null ) {
                                                       delete convergence_src._convergence_data
                                                       const pos = img_src.cur_chan
                                                       // fetch convergence information for the current channel (pos[1])
                                                       conv_pipe.send( convergence_id, { action: 'update', value: pos[1] }, update_convergence )
                                                   } else {
                                                       convergence_src._convergence_data = clean_msg.convergence
                                                       update_convergence( )
                                                   }
                                               } else {
                                                   const pos = img_src.cur_chan
                                                   // fetch convergence information for the current channel (pos[1])
                                                   conv_pipe.send( convergence_id, { action: 'update', value: pos[1] }, update_convergence )
                                               }
                                           }''',

                       'clean-disable': '''// enabling/disabling tools in self._fig['image'].toolbar.tools does not seem to not work
                                           // self._fig['image'].toolbar.tools.tool_name (e.g. "Box Select", "Lasso Select")
                                           function disable( with_stop ) {
                                               img_src.disable_masking( )
                                               niter.disabled = true
                                               cycleniter.disabled = true
                                               threshold.disabled = true
                                               cyclefactor.disabled = true
                                               btns['continue'].disabled = true
                                               btns['finish'].disabled = true
                                               slider.disabled = true
                                               image_fig.disabled = true
                                               spectra_fig.disabled = true
                                               if ( with_stop ) {
                                                   btns['stop'].disabled = true
                                               } else {
                                                   btns['stop'].disabled = false
                                               }
                                           }''',

                       'clean-enable':  '''function enable( only_stop ) {
                                               img_src.enable_masking( )
                                               niter.disabled = false
                                               cycleniter.disabled = false
                                               threshold.disabled = false
                                               cyclefactor.disabled = false
                                               niter.disabled = false
                                               btns['stop'].disabled = false
                                               slider.disabled = false
                                               image_fig.disabled = false
                                               spectra_fig.disabled = false
                                               if ( ! only_stop ) {
                                                   btns['continue'].disabled = false
                                                   btns['finish'].disabled = false
                                               }
                                           }''',


                       'slider-update': '''if ( '_convergence_data' in convergence_src ) {
                                               // use saved state for update of convergence plot if it is
                                               // available (so update can happen while tclean is running)
                                               update_convergence( )
                                           } else {
                                               // update convergence plot with a request to python
                                               conv_pipe.send( convergence_id,
                                                               { action: 'update', value: [ pos[0], cb_obj.value ] },
                                                                 //      stokes-------------^^^^^^  ^^^^^^^^^^^^^^--------chan
                                                                 update_convergence )
                                           }''',

                       'clean-status-update': '''function update_status( status ) {
                                               const stopstr = [ 'zero stop code',
                                                                 'iteration limit hit',
                                                                 'force stop',
                                                                 'no change in peak residual across two major cycles',
                                                                 'peak residual increased by 3x from last major cycle',
                                                                 'peak residual increased by 3x from the minimum',
                                                                 'zero mask found',
                                                                 'no mask found',
                                                                 'n-sigma or other valid exit criterion',
                                                                 'major cycle limit hit',
                                                                 'unrecognized stop code' ]
                                               if ( typeof status === 'number' ) {
                                                   stopstatus.text = '<div>' +
                                                                     stopstr[ status < 0 || status >= stopstr.length ?
                                                                              stopstr.length - 1 : status ] +
                                                                     '</div>'
                                               } else {
                                                   stopstatus.text = `<div>${status}</div>`
                                               }
                                           }''',

                       'clean-gui-update': '''function update_gui( msg ) {
                                               if ( msg.result === 'update' ) {
                                                   if ( 'cmd' in msg ) {
                                                       log.text = log.text + msg.cmd
                                                   }
                                                   refresh( msg )
                                                   // stopcode == 1: iteration limit hit
                                                   // stopcode == 9: major cycle limit hit
                                                   state.stopped = state.stopped || (msg.stopcode > 1 && msg.stopcode < 9) || msg.stopcode == 0
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
                                                           ctrl_pipe.send( ids[cb_obj.origin.name],
                                                                           { action: 'finish',
                                                                             value: { niter: niter.value, cycleniter: cycleniter.value,
                                                                                      threshold: threshold.value, cyclefactor: cyclefactor.value,
                                                                                      mask: img_src.masks( ),
                                                                                      breadcrumbs: img_src.breadcrumbs( ) } },
                                                                           update_gui )
                                                       } else {
                                                           state.mode = 'interactive'
                                                           btns['stop'].button_type = "danger"
                                                           enable(false)
                                                           state.stopped = false
                                                           update_status( 'stopcode' in msg ? msg.stopcode : -1 )
                                                       }
                                                   }
                                               } else if ( msg.result === 'error' ) {
                                                   img_src.drop_breadcrumb('E')
                                                   if ( 'cmd' in msg ) {
                                                       log.text = log.text + msg.cmd
                                                   }
                                                   state.mode = 'interactive'
                                                   btns['stop'].button_type = "danger"
                                                   state.stopped = false
                                                   update_status( 'stopcode' in msg ? msg.stopcode : -1 )
                                                   enable( false )
                                               }
                                           }''',

                       'clean-wait':    '''function wait_for_tclean_stop( msg ) {
                                               state.mode = 'interactive'
                                               btns['stop'].button_type = "danger"
                                               enable( false )
                                               state.awaiting_stop = false
                                               update_status( 'user requested stop' )
                                           }''',
                   }


        self._cube = CubeMask( self._residual_path, abort=self._abort_handler )
        ###
        ### error or exception result
        ###
        self._error_result = None

        ###
        ### websocket servers
        ###
        self._control_server = None
        self._converge_server = None

    def _init_pipes( self ):
        if not self.__pipes_initialized:
            self.__pipes_initialized = True
            self._pipe['control'] = DataPipe( address=find_ws_address( ), abort=self._abort_handler )
            self._pipe['converge'] = DataPipe( address=find_ws_address( ), abort=self._abort_handler )

    def _launch_gui( self ):
        '''create and show GUI
        '''
        self._fig = { }

        ###
        ### set up websockets which will be used for control and convergence updates
        ###
        self._init_pipes( )

        ###
        ### Python-side handler for events from the interactive clean control buttons
        ###
        async def clean_handler( msg, self=self ):
            if msg['action'] == 'next' or msg['action'] == 'finish':
                if 'mask' in msg['value']:
                    if 'breadcrumbs' in msg['value'] and msg['value']['breadcrumbs'] != self._last_mask_breadcrumbs:
                        self._last_mask_breadcrumbs = msg['value']['breadcrumbs']
                        mask_dir = "%s.mask" % self._imagename
                        shutil.rmtree(mask_dir)
                        new_mask = self._cube.jsmask_to_raw(msg['value']['mask'])
                        self._mask_history.append(new_mask)
                        ##msg['value']['mask'] = convert_masks( new_mask, 'region','pixel','singleton', cdesc=self._cube.coorddesc( ) )
                        msg['value']['mask'] = convert_masks( new_mask, 'crtf', 'pixel', 'list' )
                    else:
                        msg['value']['mask'] = ''
                else:
                    msg['value']['mask'] = ''
                self._clean.update( { **msg['value'], 'nmajor': 1 if msg['action'] == 'next' else -1 } )
                stopcode, self._convergence_data = await self._clean.__anext__( )
                if stopcode > 1 and stopcode < 9: # 1: iteration limit hit, 9: major cycle limit hit
                    self._clean.finalize()
                    # self._cube.update_image(self._clean.finalize()['image']) # TODO show the restored image
                if len(self._convergence_data) == 0 and stopcode == 7:
                    return dict( result='error', stopcode=stopcode, cmd=f"<p>mask error encountered (stopcode {stopcode})</p>", convergence=None  )
                if len(self._convergence_data) * len(self._convergence_data[0]) > self._threshold_chan or \
                   len(self._convergence_data[0][0]['iterations']) > self._threshold_iterations:
                    return dict( result='update', stopcode=stopcode, cmd=f'<p style="width:790px">{self._clean.cmds( )[-1]}</p>',
                                 convergence=None )
                else:
                    return dict( result='update', stopcode=stopcode, cmd=f'<p style="width:790px">{self._clean.cmds( )[-1]}</p>',
                                 convergence=self._convergence_data )

                return dict( result='update', stopcode=stopcode, cmd=f'<p style="width:790px">{self._clean.cmds( )[-1]}</p>',
                             convergence=self._convergence_data )
            elif msg['action'] == 'stop':
                self.__stop( )
                return dict( result='stopped', update=dict( ) )
            elif msg['action'] == 'status':
                return dict( result="ok", update=dict( ) )
            else:
                print( "got something else: '%s'" % msg['action'] )

        ###
        ### Setup id that will be used for messages from each button
        ###
        self._ids['clean'] = { }
        for btn in "continue", 'finish', 'stop':
            self._ids['clean'][btn] = str(uuid4( ))
            #print("%s: %s" % ( btn, self._ids['clean'][btn] ) )
            self._pipe['control'].register( self._ids['clean'][btn], clean_handler )

        ###
        ### Retrieve convergence information
        ###
        def convergence_handler( msg, self=self ):
            if msg['value'][1] in self._convergence_data:
                return { 'action': 'update-success',
                         'result': dict(converge=self._convergence_data[msg['value'][1]][msg['value'][0]]) }
                ###                                          chan-------^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^-------stokes
            else:
                return { 'action': 'update-failure' }

        self._pipe['converge'].register( self._convergence_id, convergence_handler )

        ###
        ### Data source that will be used for updating the convergence plot
        ###
        self._convergence_source = ColumnDataSource(data=self._convergence_data[0][self._stokes])

        ###
        ### Setup script that will be called when the user closes the
        ### browser tab that is running interactive clean
        ###
        self._pipe['control'].init_script = CustomJS( args=dict( convergence_src=self._convergence_source,
                                                                 ctrl_pipe=self._pipe['control'],
                                                                 ids=self._ids['clean'] ),
                                                      code=self._js['initialize'] )

        self._fig['convergence'] = figure( tooltips=[ ("x","$x"), ("y","$y"), ("value", "@image")],
                                           output_backend="webgl", plot_height=180, plot_width=800,
                                           tools=[ ],
                                           title='Convergence', x_axis_label='Iteration', y_axis_label='Peak Residual' )
        self._fig['convergence'].yaxis.axis_label_text_color = self._color['residual']
        self._fig['convergence'].extra_y_ranges = { 'modelFlux': Range1d( min(self._convergence_source.data['modelFlux'])*0.5,
                                                                     max(self._convergence_source.data['modelFlux'])*1.5 ) }
        self._fig['convergence'].add_layout( LinearAxis( y_range_name='modelFlux', axis_label='Total Flux', axis_label_text_color=self._color['flux'] ), 'right' )

        self._fig['convergence'].circle( x='iterations',
                                         y='peakRes',
                                         color=self._color['residual'],
                                         size=10,
                                         alpha=0.4,
                                         #legend_label='Peak Residual',
                                         source=self._convergence_source )
        self._fig['convergence'].circle( x='iterations',
                                         y='modelFlux',
                                         color=self._color['flux'],
                                         size=10,
                                         alpha=0.4,
                                         y_range_name='modelFlux',
                                         #legend_label='Total Flux',
                                         source=self._convergence_source )
        self._fig['convergence'].line( x='iterations',
                                       y='peakRes',
                                       color=self._color['residual'],
                                       source=self._convergence_source )

        self._fig['convergence'].line( x='iterations',
                                       y='modelFlux',
                                       color=self._color['flux'],
                                       y_range_name='modelFlux',
                                       source=self._convergence_source )

        # TClean Controls
        cwidth = 80
        cheight = 50
        self._control['clean'] = { }
        self._control['clean']['continue'] = Button( label="", max_width=cwidth, max_height=cheight, name='continue',
                                                     icon=SVGIcon(icon_name="iclean-continue", size=2.5) )
        self._control['clean']['finish'] = Button( label="", max_width=cwidth, max_height=cheight, name='finish',
                                                   icon=SVGIcon(icon_name="iclean-finish", size=2.5) )
        self._control['clean']['stop'] = Button( label="", button_type="danger", max_width=cwidth, max_height=cheight, name='stop',
                                                 icon=SVGIcon(icon_name="iclean-stop", size=2.5) )
        width = 35
        height = 35
        self._control['help'] = Button( label="", max_width=width, max_height=height, name='help',
                                        icon=SVGIcon(icon_name='help', size=1.4) )


        self._control['niter'] = TextInput( title='niter', value="%s" % self._params['niter'], width=90 )
        self._control['cycleniter'] = TextInput( title="cycleniter", value="%s" % self._params['cycleniter'], width=90 )
        self._control['threshold'] = TextInput( title="threshold", value="%s" % self._params['threshold'], width=90 )
        self._control['cycle_factor'] = TextInput( value="%s" % self._params['cyclefactor'], title="cyclefactor", width=90 )

        self._control['goto'] = TextInput( title="goto channel", value="", width=90 )

        self._fig['slider'] = self._cube.slider( )
        self._fig['image'] = self._cube.image( )
        self._fig['image-source'] = self._cube.js_obj( )
        self._fig['spectra'] = self._cube.spectra( )

        self._cb['clean'] = CustomJS( args=dict( btns=self._control['clean'],
                                                 state=dict( mode='interactive', stopped=False, awaiting_stop=False, mask="" ),
                                                 ctrl_pipe=self._pipe['control'], conv_pipe=self._pipe['converge'],
                                                 ids=self._ids['clean'],
                                                 img_src=self._fig['image-source'],
                                                 #spec_src=self._image_spectra,
                                                 niter=self._control['niter'], cycleniter=self._control['cycleniter'],
                                                 threshold=self._control['threshold'], cyclefactor=self._control['cycle_factor'],
                                                 convergence_src=self._convergence_source, convergence_id=self._convergence_id,
                                                 convergence_fig=self._fig['convergence'],
                                                 log=self._status['log'],
                                                 slider=self._fig['slider'],
                                                 image_fig=self._fig['image'],
                                                 spectra_fig=self._fig['spectra'],
                                                 stopstatus=self._status['stopcode'],
                                                 #stat_src=self._stats_source
                                                ),
                                      code=self._js['update-converge'] + self._js['clean-refresh'] + self._js['clean-disable'] +
                                           self._js['clean-enable'] + self._js['clean-status-update'] +
                                           self._js['clean-gui-update'] + self._js['clean-wait'] +
                                           '''if ( ! state.stopped && cb_obj.origin.name == 'finish' ) {
                                                  state.mode = 'continuous'
                                                  update_status( 'running multiple iterations' )
                                                  disable( false )
                                                  btns['stop'].button_type = "warning"
                                                  ctrl_pipe.send( ids[cb_obj.origin.name],
                                                                  { action: 'finish',
                                                                    value: { niter: niter.value, cycleniter: cycleniter.value,
                                                                             threshold: threshold.value, cyclefactor: cyclefactor.value,
                                                                             mask: img_src.masks( ),
                                                                             breadcrumbs: img_src.breadcrumbs( ) } },
                                                                  update_gui )
                                              }
                                              if ( ! state.stopped && state.mode === 'interactive' &&
                                                   cb_obj.origin.name === 'continue' ) {
                                                  update_status( 'running one iteration' )
                                                  disable( true )
                                                  // only send message for button that was pressed
                                                  // it's unclear whether 'this.origin.' or 'cb_obj.origin.' should be used
                                                  // (or even if 'XXX.origin.' is public)...
                                                  ctrl_pipe.send( ids[cb_obj.origin.name],
                                                                  { action: 'next',
                                                                    value: { niter: niter.value, cycleniter: cycleniter.value,
                                                                             threshold: threshold.value, cyclefactor: cyclefactor.value,
                                                                             mask: img_src.masks( ),
                                                                             breadcrumbs: img_src.breadcrumbs( ) } },
                                                                  update_gui )
                                              }
                                              if ( state.mode === 'interactive' && cb_obj.origin.name === 'stop' ) {
                                                  disable( true )
                                                  //ctrl_pipe.send( ids[cb_obj.origin.name],
                                                  //                { action: 'stop',
                                                  //                  value: { } },
                                                  //                update_gui )
                                                  img_src.done( )
                                              } else if ( state.mode === 'continuous' &&
                                                          cb_obj.origin.name === 'stop' &&
                                                          ! state.awaiting_stop ) {
                                                  disable( true )
                                                  state.awaiting_stop = true
                                                  ctrl_pipe.send( ids[cb_obj.origin.name],
                                                                  { action: 'status',
                                                                    value: { } },
                                                                  wait_for_tclean_stop )
                                              }''' )

        self._control['clean']['continue'].js_on_click( self._cb['clean'] )
        self._control['clean']['finish'].js_on_click( self._cb['clean'] )
        self._control['clean']['stop'].js_on_click( self._cb['clean'] )

        self._fig['slider'].js_on_change( 'value',
                                          CustomJS( args=dict( convergence_src=self._convergence_source,
                                                               convergence_fig=self._fig['convergence'],
                                                               conv_pipe=self._pipe['converge'], convergence_id=self._convergence_id,
                                                               img_src=self._fig['image-source']
                                                             ),
                                                    code='''const pos = img_src.cur_chan;''' +             ### later we will receive the polarity from some widget mechanism...
                                                            self._js['update-converge'] + self._js['slider-update'] ) )
        
        # Generates the HTML for the controls layout:
        # niter cycleniter cycle_factor threshold  -----------
        #                  slider                  -  image  -
        # goto               continue finish stop  -----------
        # status: stopcode                  stats         help
        # spectra
        # convergence
        # log
        self._fig['layout'] = column(
                                  row(
                                      column(
                                          row( self._control['niter'],
                                               self._control['cycleniter'],
                                               self._control['cycle_factor'],
                                               self._control['threshold'] ),
                                          self._fig['slider'],
                                          row( self._control['goto'],
                                               self._control['clean']['continue'],
                                               self._control['clean']['finish'],
                                               self._control['clean']['stop'] ),
                                          row ( Div( text="<div><b>status:</b></div>" ), self._status['stopcode'] ),
                                          self._cube.statistics( sizing_mode = "stretch_height" ),
                                      ),
                                      column( self._fig['image'],
                                              row( Spacer(height=self._control['help'].height, sizing_mode="scale_width"),
                                                   self._control['help'],
                                                   Spacer(height=self._control['help'].height, width=30)
                                              )
                                      ),
                                      self._cube.help( width=450, height=100,
                                                       rows=[ '<tr><td><i><b>red</b> stop button</i></td><td>clicking the stop button (when red) will close the dialog and control to python</td></tr>',
                                                              '<tr><td><i><b>orange</b> stop button</i></td><td>clicking the stop button (when orang) will return control to the GUI after the currently executing tclean run completes</td></tr>',

                                                             ]
                                                     )
                                  ),
                                  self._fig['spectra'],
                                  self._fig['convergence'],
                                  Spacer(width=380, height=40, sizing_mode='scale_width'),
                                  self._status['log'] )

        self._control['help'].js_on_click( CustomJS( args=dict( help=self._cube.help( ) ),
                                                     code='''if ( help.visible == true ) help.visible = false
                                                             else help.visible = true''' ) )
        self._cube.connect( )
        show(self._fig['layout'])

    def _asyncio_loop( self ):
        async def async_loop( f1, f2, f3 ):
            return await asyncio.gather( f1, f2, f3 )

        self._control_server = websockets.serve( self._pipe['control'].process_messages, self._pipe['control'].address[0], self._pipe['control'].address[1] )
        self._converge_server = websockets.serve( self._pipe['converge'].process_messages, self._pipe['converge'].address[0], self._pipe['converge'].address[1] )
        resource_manager.reg_webserver(self._control_server.ws_server)
        resource_manager.reg_webserver(self._converge_server.ws_server)
        return async_loop( self._control_server, self._converge_server, self._cube.loop( ) )

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
        '''Get the InteractiveClean event loop to use for running the interactive clean GUI
        as part of an external event loop.
        '''
        self._launch_gui( )
        return self._asyncio_loop( )

    def result( self ):
        '''If InteractiveClean had a return value, it would be filled in as part of the
        GUI dialog between Python and JavaScript and this function would return it'''
        if isinstance(self._error_result,Exception):
            raise self._error_result
        elif self._error_result is not None:
            return self._error_result
        return self._cube.result( )

    def masks( self ):
        '''Retrieves the masks which were used with interactive clean.

        Returns
        -------
        The standard ``casagui`` cube region dictionary which contains two elements
        ``masks`` and ``polys``.

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

        This can be converted to other formats with ``casagui.utils.convert_masks``.
        '''
        return copy.deepcopy(self._mask_history)    ## don't allow users to change history
