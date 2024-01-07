########################################################################
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
'''implementation of the ``InteractiveClean`` application for interactive control
of tclean'''
import os
import copy
import asyncio
import shutil
import websockets
from uuid import uuid4
from html import escape as html_escape
from contextlib import asynccontextmanager
from bokeh.models import Button, TextInput, Div, LinearAxis, CustomJS, Spacer, Span, HoverTool, DataRange1d, Step
from bokeh.events import ModelEvent, MouseEnter
from bokeh.models import TabPanel, Tabs
from bokeh.plotting import ColumnDataSource, figure, show
from bokeh.layouts import column, row, Spacer, layout
from bokeh.io import reset_output as reset_bokeh_output, output_notebook
from bokeh.models.dom import HTML

from bokeh.models.ui.tooltips import Tooltip
from ..bokeh.models import TipButton, Tip
from ..utils import resource_manager, reset_resource_manager, is_notebook
from casatasks.private.imagerhelpers.imager_return_dict import ImagingDict

try:
    ## gclean version number needed for proper interactive clean behavior
    # pylint: disable=no-name-in-module
    from casatasks.private.imagerhelpers._gclean import _GCV004
    from casatasks.private.imagerhelpers._gclean import gclean as _gclean
    # pylint: enable=no-name-in-module
except:
    try:
        ###
        ### enable this warning when casa6 a usable _gclean.py (i.e. compatibility is not the default)
        ###
        #print('warning: using tclean compatibility layer...')
        from ..private.compatibility.casatasks.private.imagerhelpers._gclean import _GCV004
        from ..private.compatibility.casatasks.private.imagerhelpers._gclean import gclean as _gclean
    except:
        _gclean = None
        from casagui.utils import warn_import
        warn_import('casatasks')

from casagui.utils import find_ws_address, convert_masks
from casagui.toolbox import CubeMask, AppContext
from casagui.bokeh.components import svg_icon
from casagui.bokeh.sources import DataPipe
from ..utils import DocEnum

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
    allow the user to set the ``nmajor``, ``niter``, ``cycleiter``, ``cyclefactor``, and ``threshold``.
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
        usemask (str): indicates the type of masking to be used, supported values are 'user', 'auto-multithresh' and 'pb'
        mask (str): user specified CASA imaging mask cube (path) to use when :code:`usemask` mode is 'user'
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
        nmajor (int): Maximum number of major cycle iterations
        niter (int): Maximum total number of iterations
        threshold (str | float): Stopping threshold (number in units of Jy, or string).
        cycleniter (int): Maximum number of minor-cycle iterations (per plane) before triggering a major cycle
        cyclefactor (float): Scaling on PSF sidelobe level to compute the minor-cycle stopping threshold.
        scales (:obj:`list` of int): List of scale sizes (in pixels) for multi-scale algorithms

    '''
    def __stop( self ):
        self.__result_future.set_result(self.__retrieve_result( ))

    def _abort_handler( self, err ):
        self._error_result = err
        self.__stop( )

    def __reset( self ):
        if self.__pipes_initialized:
            self._pipe = { 'control': None, 'converge': None }
            reset_bokeh_output( )
            reset_resource_manager( )
            self._clean.reset( )

        ###
        ### reset asyncio result future
        ###
        self.__result_future = None

        ###
        ### used by data pipe (websocket) initialization function
        ###
        self.__pipes_initialized = False
        self._mask_history = [ ]

        self._cube = CubeMask( self._residual_path, mask=self._clean.mask( ), abort=self._abort_handler )
        ###
        ### error or exception result
        ###
        self._error_result = None

        ###
        ### websocket servers
        ###
        self._control_server = None
        self._converge_server = None

    '''
        _gen_port_fwd_cmd()

    Create an SSH port-forwarding command to create the tunnels necessary for remote connection.
    NOTE: This assumes that the same remote ports are also available locally - which may
        NOT always be true.
    '''
    def _gen_port_fwd_cmd(self):
        hostname = os.uname()[1]

        ports = [self._pipe['control'].address[1],
                self._pipe['converge'].address[1],
                self._cube._pipe['image'].address[1],
                self._cube._pipe['control'].address[1]]

        # Also forward http port if serving webpage
        if not self._is_notebook:
            ports.append(self._http_port)

        cmd = 'ssh'
        for port in ports:
            cmd += (' -L ' + str(port) + ':localhost:' + str(port))

        cmd += ' ' + str(hostname)
        return cmd

    def __init__( self, vis, imagename, usemask='user', mask='', initial_mask_pixel=False, field='', spw='', timerange='', uvrange='', antenna='', scan='', observation='', intent='',
                  datacolumn='corrected', nterms=int(2), imsize=[100], cell=[ ], phasecenter='', stokes='I', startmodel='', specmode='cube', reffreq='',
                  nchan=-1, start='', width='', veltype='radio', restfreq='', outframe='LSRK', interpolation='linear', perchanweightdensity=True, gridder='standard',
                  wprojplanes=int(1), mosweight=True, psterm=False, wbawp=True, usepointing=False, conjbeams=False, pointingoffsetsigdev=[  ], pblimit=0.2,
                  deconvolver='hogbom', niter=0, threshold='0.1Jy', nsigma=0.0, cycleniter=-1, cyclefactor=1.0, scales=[], restoringbeam='',
                  smallscalebias=0.0, pbcor=False, weighting='natural', robust=float(0.5), npixels=0, gain=float(0.1), sidelobethreshold=3.0, noisethreshold=5.0,
                  lownoisethreshold=1.5, negativethreshold=0.0, minbeamfrac=0.3, growiterations=75, dogrowprune=True, minpercentchange=-1.0,
                  fastnoise=True, savemodel='none', parallel=False, nmajor=-1, remote=False):

        ###
        ### Create application context (which includes a temporary directory).
        ### This sets the title of the plot.
        ###
        self._app_state = AppContext( 'Interactive Clean' )

        ###
        ### Whether or not the Interactive Clean session is running remotely
        ###
        self._is_remote = remote

        ###
        ### whether or not the session is being run from a jupyter notebook or script
        ###
        self._is_notebook = is_notebook()

        ##
        ## the http port for serving GUI in webpage if not running in script
        ##
        self._http_port = None

        ###
        ### the asyncio future that is used to transmit the result from interactive clean
        ###
        self.__result_future = None

        ###
        ### This is used to tell whether the websockets have been initialized, but also to
        ### indicate if __call__ is being called multiple times to allow for resetting Bokeh
        ###
        self.__pipes_initialized = False

        ###
        ### color specs
        ###
        self._color = { 'residual': 'black',
                        'flux':     'forestgreen' }

        ###
        ### Auto Masking et al.
        self._usemask = 'user'

        ###
        ### If the user has supplied a mask, do NOT modify it after initial tclean/deconvolve call...
        ### otherwise if the 'initial_mask_pixel' is a boolean then initialize the mask pixels
        ### to 'initial_mask_pixel' before loading the GUI...
        ###
        if type(initial_mask_pixel) is bool:
            self._reset_mask_pixels = True
            self._reset_mask_pixels_value = initial_mask_pixel
        else:
            self._reset_mask_pixels = False
            self._reset_mask_pixels_value = None

        ###
        ### set up masking mode based on 'usemask' and 'mask'
        ###
        if usemask == 'auto-multithresh':
            self._usemask = 'auto-multithresh'
        elif usemask == 'pb':
            self._usemask = 'pb'
        elif usemask == 'user':
            if mask != '':
                if isinstance( mask, str ) and os.path.isdir( mask ):
                    ### user has supplied a mask on disk
                    self._reset_mask_pixels = False
                else:
                    raise RuntimeError( f'''user supplied mask does not exist or is not a directory: {mask}''' )
        else:
            raise RuntimeError( f'''unrecognized mask type: {usemask}''' )

        ###
        ### clean generator
        ###
        if _gclean is None:
            raise RuntimeError('casatasks gclean interface is not available')

        self._clean = _gclean( vis=vis, imagename=imagename, field=field, spw=spw, timerange=timerange,  uvrange=uvrange, antenna=antenna, scan=scan,
                               observation=observation, intent=intent, datacolumn=datacolumn, nterms=nterms, imsize=imsize, cell=cell,
                               phasecenter=phasecenter, stokes=stokes, startmodel=startmodel, specmode=specmode, reffreq=reffreq, nchan=nchan,
                               start=start, width=width, outframe=outframe, veltype=veltype, restfreq=restfreq, interpolation=interpolation,
                               perchanweightdensity=perchanweightdensity, gridder=gridder, wprojplanes=wprojplanes, mosweight=mosweight, psterm=psterm,
                               wbawp=wbawp, usepointing=usepointing, conjbeams=conjbeams, pointingoffsetsigdev=pointingoffsetsigdev, pblimit=pblimit,
                               deconvolver=deconvolver, smallscalebias=smallscalebias, niter=niter, threshold=threshold, nsigma=nsigma,
                               cycleniter=cycleniter, cyclefactor=cyclefactor, scales=scales, restoringbeam=restoringbeam, pbcor=pbcor,
                               weighting=weighting, robust=robust, npixels=npixels, gain=gain, sidelobethreshold=sidelobethreshold,
                               noisethreshold=noisethreshold, lownoisethreshold=lownoisethreshold, negativethreshold=negativethreshold,
                               minbeamfrac=minbeamfrac, growiterations=growiterations, dogrowprune=dogrowprune,
                               minpercentchange=minpercentchange, fastnoise=fastnoise, savemodel=savemodel, parallel=parallel, nmajor=nmajor,
                               usemask=self._usemask, mask=mask
                      )
        ###
        ### self._convergence_data['chan']: accumulated, pre-channel convergence information
        ###                                 used by ColumnDataSource
        ###
        self._status = { }
        stopdesc, stopcode, majordone, majorleft, iterleft, self._convergence_data = next(self._clean)
        if self._convergence_data['chan'] is None or len(self._convergence_data['chan'].keys()) == 0:
            raise RuntimeError(stopdesc)
        self._convergence_id = str(uuid4( ))
        #print(f'convergence:',self._convergence_id)

        ###
        ### Initial Conditions
        ###
        self._params = { }
        self._params['nmajor'] = majorleft
        self._params['niter'] = iterleft
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
        # Create folder for the generated html webpage - needs its own folder to not name conflict (must be 'index.html')
        webpage_dirname = imagename + '_webpage'
        ### Directory is created when an HTTP server is running
        ### (MAX)
#       if not os.path.isdir(webpage_dirname):
#          os.makedirs(webpage_dirname)
        self._webpage_path = os.path.abspath(webpage_dirname)
        if deconvolver == 'mtmfs':
            self._residual_path = ("%s.residual.tt0" % imagename) if self._clean.has_next() else (self._clean.finalize()['image'])
        else:
            self._residual_path = ("%s.residual" % imagename) if self._clean.has_next() else (self._clean.finalize()['image'])
        self._pipe = { 'control': None, 'converge': None }
        self._control = { }
        self._cb = { }
        self._ids = { }
        self._last_mask_breadcrumbs = ''
        ###
        ### tclean/deconvolve log page
        ###
        self.__log_button = None
        ###
        ### ColumnDataSource for convergence plot
        ###
        self._flux_data     = None
        self._residual_data = None

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
                     ### -- flux_src is used storing state (initialized and convergence data cache below   --
                     ### --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
                     'initialize':      '''if ( ! flux_src._initialized ) {
                                               flux_src._initialized = true
                                               flux_src._window_closed = false
                                               window.addEventListener( 'beforeunload',
                                                                        function (e) {
                                                                            // if the window is already closed this message is never
                                                                            // delivered (unless interactive clean is called again then
                                                                            // the event shows up in the newly created control pipe
                                                                            if ( flux_src._window_closed == false ) {
                                                                                ctrl_pipe.send( ids['stop'],
                                                                                                { action: 'stop', value: { } },
                                                                                                  undefined ) } } )
                                           }''',

                     ### --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
                     ### -- flux_src._convergence_data is used to store the complete                       --
                     ### --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
                     'update-converge': '''function update_convergence( msg ) {
                                               let convdata
                                               if ( typeof msg === 'undefined' && '_convergence_data' in flux_src ) {
                                                   // use complete convergence cache attached to flux_src...
                                                   // get the convergence data for channel and stokes
                                                   const pos = img_src.cur_chan
                                                   convdata = flux_src._convergence_data.chan.get(pos[1]).get(pos[0])
                                                   //          chan-------------------------------^^^^^^      ^^^^^^----stokes
                                               } else if ( 'result' in msg ) {
                                                   // update based on msg received from convergence update message
                                                   convdata = msg.result.converge
                                               }
                                               const iterations = convdata.iterations
                                               const peakRes = convdata.peakRes
                                               const threshold = convdata.cycleThresh
                                               const modelFlux = convdata.modelFlux
                                               const stopCode = convdata.stopCode
                                               const stopDesc = convdata.stopCode.map( code => stopdescmap.has(code) ? stopdescmap.get(code): "" )
                                               residual_src.data = { iterations, threshold, stopDesc, values: peakRes, type: Array(iterations.length).fill('residual') }
                                               flux_src.data = { iterations, threshold, stopDesc, values: modelFlux, type: Array(iterations.length).fill('flux') }
                                               threshold_src.data = { iterations, values: threshold }
                                           }''',

                     'clean-refresh':   '''function refresh( clean_msg ) {
                                               let stokes = 0    // later we will receive the polarity
                                                                 // from some widget mechanism...
                                               //img_src.refresh( msg => { if ( 'stats' in msg ) { //  -- this should happen within CubeMask
                                               //                              stat_src.data = msg.stats
                                               //                          }
                                               //                        } )
                                               if ( clean_msg !== undefined ) {
                                                   if ( 'iterleft' in clean_msg ) {
                                                       niter.value = '' + clean_msg['iterleft']
                                                   } else if ( clean_msg !== undefined && 'iterdone' in clean_msg ) {
                                                       const remaining = parseInt(niter.value) - parseInt(clean_msg['iterdone'])
                                                       niter.value = '' + (remaining < 0 ? 0 : remaining)
                                                   }

                                                   if ( 'majorleft' in clean_msg ) {
                                                       nmajor.value = '' + clean_msg['majorleft']
                                                   } else if ( 'majordone' in clean_msg ) {
                                                       const nm = parseInt(nmajor.value)
                                                       if ( nm != -1 ) {
                                                           const remaining = nm - parseInt(clean_msg['majordone'])
                                                           nmajor.value = '' + (remaining < 0 ? 0 : remaining)
                                                       } else nmajor.value = '' + nm          // nmajor == -1 implies do not consider nmajor in stop decision
                                                   }
                                               }

                                               img_src.refresh( (data) => { if ( 'stats' in data ) cube_obj.update_statistics( data.stats ) } )

                                               if ( clean_msg !== undefined && 'convergence' in clean_msg ) {
                                                   // save convergence information and update convergence using saved state
                                                   if ( clean_msg.convergence === null ) {
                                                       delete flux_src._convergence_data
                                                       const pos = img_src.cur_chan
                                                       // fetch convergence information for the current channel (pos[1])
                                                       // ...convergence update expects [ stokes, chan ]
                                                       conv_pipe.send( convergence_id, { action: 'update', value: pos }, update_convergence )
                                                   } else {
                                                       flux_src._convergence_data = { chan: clean_msg.convergence,
                                                                                      cyclethreshold: clean_msg.cyclethreshold }
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
                                               nmajor.disabled = true
                                               niter.disabled = true
                                               cycleniter.disabled = true
                                               threshold.disabled = true
                                               cyclefactor.disabled = true
                                               btns['continue'].disabled = true
                                               btns['finish'].disabled = true
                                               if ( slider ) slider.disabled = true
                                               if ( go_to ) go_to.disabled = true
                                               image_fig.disabled = true
                                               if ( spectra_fig ) spectra_fig.disabled = true
                                               if ( with_stop ) {
                                                   btns['stop'].disabled = true
                                               } else {
                                                   btns['stop'].disabled = false
                                               }
                                           }''',

                       'clean-enable':  '''function enable( only_stop ) {
                                               img_src.enable_masking( )
                                               nmajor.disabled = false
                                               niter.disabled = false
                                               cycleniter.disabled = false
                                               threshold.disabled = false
                                               cyclefactor.disabled = false
                                               btns['stop'].disabled = false
                                               if ( slider ) slider.disabled = false
                                               if ( go_to ) go_to.disabled = false
                                               image_fig.disabled = false
                                               if ( spectra_fig ) spectra_fig.disabled = false
                                               if ( ! only_stop ) {
                                                   btns['continue'].disabled = false
                                                   btns['finish'].disabled = false
                                               }
                                           }''',


                       'slider-update': '''if ( '_convergence_data' in flux_src ) {
                                               // use saved state for update of convergence plot if it is
                                               // available (so update can happen while tclean is running)
                                               update_convergence( )
                                           } else {
                                               // update convergence plot with a request to python
                                               const pos = img_src.cur_chan
                                               conv_pipe.send( convergence_id,
                                                               { action: 'update', value: [ pos[0], cb_obj.value ] },
                                                                 //      stokes-------------^^^^^^  ^^^^^^^^^^^^^^--------chan
                                                                 update_convergence )
                                           }''',

                       'clean-status-update': '''function update_status( status ) {
                                               const stopstr = [ 'Zero stop code',
                                                                 'Iteration limit hit',
                                                                 'Force stop',
                                                                 'No change in peak residual across two major cycles',
                                                                 'Peak residual increased by 3x from last major cycle',
                                                                 'Peak residual increased by 3x from the minimum',
                                                                 'Zero mask found',
                                                                 'No mask found',
                                                                 'N-sigma or other valid exit criterion',
                                                                 'Stopping criteria encountered',
                                                                 'Unrecognized stop code' ]
                                               if ( typeof status === 'number' ) {
                                                   stopstatus.text = '<div>' +
                                                                     stopstr[ status < 0 || status >= stopstr.length ?
                                                                              stopstr.length - 1 : status ] +
                                                                     '</div>'
                                               } else {
                                                   stopstatus.text = `<div>${status}</div>`
                                               }
                                           }''',

                       'clean-gui-update': '''function update_log( log_lines ) {
                                               let b = logbutton
                                               b._log = b._log.concat( log_lines )
                                               if ( b._window && ! b._window.closed ) {
                                                   for ( const line of log_lines ) {
                                                       const p = b._window.document.createElement('p')
                                                       p.appendChild( b._window.document.createTextNode(line) )
                                                       b._window.document.body.appendChild(p)
                                                   }
                                               }
                                           }
                                           function update_gui( msg ) {
                                               if ( msg.result === 'error' ) {
                                                   // ************************************************************************************
                                                   // ******** error occurs and is signaled by _gclean, e.g. exception in gclean  ********
                                                   // ************************************************************************************
                                                   state.mode = 'interactive'
                                                   btns['stop'].button_type = "danger"
                                                   enable(false)
                                                   state.stopped = false
                                                   update_status( msg.stopdesc ? msg.stopdesc : 'An internal error has occurred' )
                                                   if ( 'cmd' in msg ) {
                                                       update_log( msg.cmd )
                                                   }
                                               } else if ( msg.result === 'no-action' ) {
                                                   update_status( msg.stopdesc ? msg.stopdesc : 'nothing done' )
                                                   enable( false )
                                                   if ( 'cmd' in msg ) {
                                                       update_log( msg.cmd )
                                                   }
                                               } else if ( msg.result === 'update' ) {
                                                   if ( 'cmd' in msg ) {
                                                       update_log( msg.cmd )
                                                   }
                                                   refresh( msg )
                                                   // stopcode == 1: iteration limit hit
                                                   // stopcode == 9: major cycle limit hit
                                                   // *******************************************************************************************
                                                   // ******** perhaps the user should not be locked into exiting after the limit is hit ********
                                                   // *******************************************************************************************
                                                   //state.stopped = state.stopped || (msg.stopcode > 1 && msg.stopcode < 9) || msg.stopcode == 0
                                                   state.stopped = false
                                                   if ( state.mode === 'interactive' && ! state.awaiting_stop ) {
                                                       btns['stop'].button_type = "danger"
                                                       update_status( msg.stopdesc ? msg.stopdesc : 'stopcode' in msg ? msg.stopcode : -1 )
                                                       if ( ! state.stopped ) {
                                                           enable( false )
                                                       } else {
                                                           disable( false )
                                                       }
                                                   } else if ( state.mode === 'continuous' && ! state.awaiting_stop ) {
                                                       if ( ! state.stopped && niter.value > 0 && (nmajor.value > 0 || nmajor.value == -1) ) {
                                                           // *******************************************************************************************
                                                           // ******** 'niter.value > 0 so continue with one more iteration                      ********
                                                           // ******** 'nmajor.value' == -1 implies do not consider nmajor in stop consideration ********
                                                           // *******************************************************************************************
                                                           ctrl_pipe.send( ids[cb_obj.origin.name],
                                                                           { action: 'finish',
                                                                             value: { niter: niter.value, cycleniter: cycleniter.value, nmajor: nmajor.value,
                                                                                      threshold: threshold.value, cyclefactor: cyclefactor.value,
                                                                                      mask: img_src.masks( ),
                                                                                      breadcrumbs: img_src.breadcrumbs( ) } },
                                                                           update_gui )
                                                       } else if ( ! state.stopped  ) {
                                                           // *******************************************************************************************
                                                           // ******** 'niter.value <= 0 so iteration should stop                                ********
                                                           // *******************************************************************************************
                                                           state.mode = 'interactive'
                                                           btns['stop'].button_type = "danger"
                                                           enable(false)
                                                           state.stopped = false
                                                           update_status( msg.stopdesc ? msg.stopdesc : 'stopping criteria reached' )
                                                       } else {
                                                           state.mode = 'interactive'
                                                           btns['stop'].button_type = "danger"
                                                           enable(false)
                                                           state.stopped = false
                                                           update_status( msg.stopdesc ? msg.stopdesc : 'stopcode' in msg ? msg.stopcode : -1 )
                                                       }
                                                   }
                                               } else if ( msg.result === 'error' ) {
                                                   img_src.drop_breadcrumb('E')
                                                   if ( 'cmd' in msg ) {
                                                       update_log( msg.cmd )
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


    def _init_pipes( self ):
        if not self.__pipes_initialized:
            self.__pipes_initialized = True
            self._pipe['control'] = DataPipe( address=find_ws_address( ), abort=self._abort_handler )
            self._pipe['converge'] = DataPipe( address=find_ws_address( ), abort=self._abort_handler )

            # Get port for serving HTTP server if running in script
            self._http_port = find_ws_address("")[1]

    def _launch_gui( self ):
        '''create and show GUI
        '''
        image_channels = self._cube.shape( )[3]

        self._fig = { }

        ###
        ### set up websockets which will be used for control and convergence updates
        ###
        self._init_pipes( )

        self._status['log'] = self._clean.cmds( )
        self._status['stopcode']= self._cube.status_text( "<div>initial residual image</div>" if image_channels > 1 else "<div>initial <b>single-channel</b> residual image</div>" )

        ###
        ### Python-side handler for events from the interactive clean control buttons
        ###
        async def clean_handler( msg, self=self ):
            if msg['action'] == 'next' or msg['action'] == 'finish':

                if 'mask' in msg['value']:
                    if 'breadcrumbs' in msg['value'] and msg['value']['breadcrumbs'] is not None and msg['value']['breadcrumbs'] != self._last_mask_breadcrumbs:
                        self._last_mask_breadcrumbs = msg['value']['breadcrumbs']
                        mask_dir = "%s.mask" % self._imagename
                        shutil.rmtree(mask_dir)
                        new_mask = self._cube.jsmask_to_raw(msg['value']['mask'])
                        self._mask_history.append(new_mask)

                        msg['value']['mask'] = convert_masks(masks=new_mask, coord='pixel', cdesc=self._cube.coorddesc())

                    else:
                        ##### seemingly the mask path used to be spliced in?
                        #msg['value']['mask'] = self._mask_path
                        pass
                else:
                    ##### seemingly the mask path used to be spliced in?
                    #msg['value']['mask'] = self._mask_path
                    pass

                err,errmsg = self._clean.update( dict( niter=msg['value']['niter'],
                                                       cycleniter=msg['value']['cycleniter'],
                                                       nmajor=msg['value']['nmajor'],
                                                       threshold=msg['value']['threshold'],
                                                       cyclefactor=msg['value']['cyclefactor'] ) )

                if err: return dict( result='no-action', stopcode=1, iterdone=0, majordone=0, stopdesc=html_escape(errmsg) )

                iteration_limit = int(msg['value']['niter'])
                stopdesc, stopcode, majordone, majorleft, iterleft, self._convergence_data = await self._clean.__anext__( )

                if len(self._convergence_data['chan']) == 0 and stopcode == 7 or stopcode == -1:
                    ### stopcode == -1 indicates an error condition within gclean
                    return dict( result='error', stopcode=stopcode, cmd=self._clean.cmds( ),
                                 convergence=None, majordone=majordone,
                                 majorleft=majorleft, iterleft=iterleft, stopdesc=stopdesc )
                if len(self._convergence_data['chan']) == 0:
                    return dict( result='no-action', stopcode=stopcode, cmd=self._clean.cmds( ),
                                 convergence=None, iterdone=0, iterleft=iterleft,
                                 majordone=majordone, majorleft=majorleft, stopdesc=stopdesc )
                if len(self._convergence_data['chan']) * len(self._convergence_data['chan'][0]) > self._threshold_chan or \
                   len(self._convergence_data['chan'][0][0]['iterations']) > self._threshold_iterations:
                    return dict( result='update', stopcode=stopcode, cmd=self._clean.cmds( ), convergence=None,
                                 iterdone=iteration_limit - iterleft, iterleft=iterleft,
                                 majordone=majordone, majorleft=majorleft, stopdesc=stopdesc )
                else:
                    return dict( result='update', stopcode=stopcode, cmd=self._clean.cmds( ),
                                 convergence=self._convergence_data['chan'],
                                 iterdone=iteration_limit - iterleft, iterleft=iterleft,
                                 majordone=majordone, majorleft=majorleft, cyclethreshold=self._convergence_data['major']['cyclethreshold'], stopdesc=stopdesc )

                return dict( result='update', stopcode=stopcode, cmd=self._clean.cmds( ),
                             convergence=self._convergence_data['chan'],
                             iterdone=iteration_limit - iterleft, iterleft=iterleft,
                             majordone=majordone, majorleft=majorleft, cyclethreshold=self._convergence_data['major']['cyclethreshold'], stopdesc=stopdesc )
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
            if msg['value'][1] in self._convergence_data['chan']:
                return { 'action': 'update-success',
                         'result': dict(converge=self._convergence_data['chan'][msg['value'][1]][msg['value'][0]],
                ###                                                  chan-------^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^-------stokes
                                        cyclethreshold=self._convergence_data['major']['cyclethreshold']) }
            else:
                return { 'action': 'update-failure' }

        self._pipe['converge'].register( self._convergence_id, convergence_handler )

        ###
        ### Data source that will be used for updating the convergence plot
        ###
        convergence = self._convergence_data['chan'][0][self._stokes]
        self._flux_data     = ColumnDataSource( data=dict( values=convergence['modelFlux'], iterations=convergence['iterations'],
                                                           threshold=convergence['cycleThresh'],
                                                           stopDesc=list( map( ImagingDict.get_summaryminor_stopdesc, convergence['stopCode'] ) ),
                                                           type=['flux'] * len(convergence['iterations']) ) )
        self._residual_data = ColumnDataSource( data=dict( values=convergence['peakRes'],   iterations=convergence['iterations'],
                                                           threshold=convergence['cycleThresh'],
                                                           stopDesc=list( map( ImagingDict.get_summaryminor_stopdesc, convergence['stopCode'] ) ),
                                                           type=['residual'] * len(convergence['iterations'])) )
        self._cyclethreshold_data = ColumnDataSource( data=dict( values=convergence['cycleThresh'], iterations=convergence['iterations'] ) )


        ###
        ### help page for cube interactions
        ###
        help_button = self._cube.help( rows=[ '<tr><td><i><b>red</b> stop button</i></td><td>clicking the stop button (when red) will close the dialog and control to python</td></tr>',
                                              '<tr><td><i><b>orange</b> stop button</i></td><td>clicking the stop button (when orang) will return control to the GUI after the currently executing tclean run completes</td></tr>' ] )

        ###
        ### button to display the tclean log
        ###
        self.__log_button = TipButton( max_width=help_button.width, max_height=help_button.height, name='log',
                                       icon=svg_icon(icon_name="iclean-log", size=25),
                                       tooltip=Tooltip( content=HTML('''click here to see the <pre>tclean</pre> execution log'''), position="bottom" ),
                                       margin=(-1, 0, -10, 0), button_type='light' )
        self.__log_button.js_on_click( CustomJS( args=dict( logbutton=self.__log_button ),
                                                 code='''function format_log( elem ) {
                                                             return `<html>
                                                                     <head>
                                                                         <style type="text/css">
                                                                             body {
                                                                                 counter-reset: section;
                                                                             }
                                                                             p:before {
                                                                                 font-weight: bold;
                                                                                 counter-increment: section;
                                                                                 content: "" counter(section) ": ";
                                                                             }
                                                                         </style>
                                                                     </head>
                                                                     <body>
                                                                         <h1>Interactive Clean History</h1>
                                                                     ` + elem.map((x) => `<p>${x}</p>`).join('\\n') + '</body>\\n</html>'
                                                         }
                                                         let b = cb_obj.origin
                                                         if ( ! b._window || b._window.closed ) {
                                                             b._window = window.open("about:blank","Interactive Clean Log")
                                                             b._window.document.write(format_log(b._log))
                                                             b._window.document.close( )
                                                         }''' ) )

        ###
        ### Setup script that will be called when the user closes the
        ### browser tab that is running interactive clean
        ###
        self._pipe['control'].init_script = CustomJS( args=dict( flux_src=self._flux_data,
                                                                 residual_src=self._residual_data,
                                                                 ctrl_pipe=self._pipe['control'],
                                                                 ids=self._ids['clean'],
                                                                 logbutton=self.__log_button,
                                                                 log=self._status['log'] ),
                                                      code=self._js['initialize'] +
                                                           '''if ( ! logbutton._log ) {
                                                                  /*** store log list with log button for access in other callbacks ***/
                                                                  logbutton._log = log
                                                              }''' )

        TOOLTIPS='''<div>
                        <div>
                            <span style="font-weight: bold;">@type</span>
                            <span>@values</span>
                        </div>
                        <div>
                            <span style="font-weight: bold; font-size: 10px">cycle threshold</span>
                            <span>@threshold</span>
                        </div>
                        <div>
                            <span style="font-weight: bold; font-size: 10px">stop</span>
                            <span>@stopDesc</span>
                        </div>
                    </div>'''

        hover = HoverTool( tooltips=TOOLTIPS )
        self._fig['convergence'] = figure( height=180, width=450, tools=[ hover ], title='Convergence',
                                           x_axis_label='Iteration (cycle threshold dotted red)', y_axis_label='Peak Residual',
                                           sizing_mode='stretch_width' )

        self._fig['convergence'].extra_y_ranges = { 'residual_range': DataRange1d( ),
                                                    'flux_range': DataRange1d( ) }

        self._fig['convergence'].step( 'iterations', 'values', source=self._cyclethreshold_data,  line_color='red',              y_range_name='residual_range',
                                       line_dash='dotted', line_width=2 )
        self._fig['convergence'].line(   'iterations', 'values',   source=self._residual_data, line_color=self._color['residual'], y_range_name='residual_range' )
        self._fig['convergence'].circle( 'iterations', 'values',   source=self._residual_data,      color=self._color['residual'], y_range_name='residual_range',size=10 )
        self._fig['convergence'].line(   'iterations', 'values', source=self._flux_data,     line_color=self._color['flux'],     y_range_name='flux_range' )
        self._fig['convergence'].circle( 'iterations', 'values', source=self._flux_data,          color=self._color['flux'],     y_range_name='flux_range', size=10 )

        self._fig['convergence'].add_layout( LinearAxis( y_range_name='flux_range', axis_label='Total Flux',
                                                         axis_line_color=self._color['flux'],
                                                         major_label_text_color=self._color['flux'],
                                                         axis_label_text_color=self._color['flux'],
                                                         major_tick_line_color=self._color['flux'],
                                                         minor_tick_line_color=self._color['flux'] ), 'right')

        # TClean Controls
        cwidth = 80
        cheight = 50
        self._control['clean'] = { }
        self._control['clean']['continue'] = TipButton( max_width=cwidth, max_height=cheight, name='continue',
                                                        icon=svg_icon(icon_name="iclean-continue", size=25),
                                                        tooltip=Tooltip( content=HTML( '''Stop after <b>one major cycle</b> or when any stopping criteria is met.''' ), position='bottom') )
        self._control['clean']['finish'] = TipButton( max_width=cwidth, max_height=cheight, name='finish',
                                                      icon=svg_icon(icon_name="iclean-finish", size=25),
                                                      tooltip=Tooltip( content=HTML( '''<b>Continue</b> until some stopping criteria is met.''' ), position='bottom') )
        self._control['clean']['stop'] = TipButton( button_type="danger", max_width=cwidth, max_height=cheight, name='stop',
                                                    icon=svg_icon(icon_name="iclean-stop", size=25),
                                                    tooltip=Tooltip( content=HTML( '''Clicking a <font color="red">red</font> stop button will cause this tab to close and control will return to Python.<p>Clicking an <font color="orange">orange</font> stop button will cause <tt>tclean</tt> to stop after the current major cycle.''' ), position='bottom' ) )
        self._control['nmajor'] = TextInput( title='nmajor', value="%s" % self._params['nmajor'], width=90 )
        self._control['niter'] = TextInput( title='niter', value="%s" % self._params['niter'], width=90 )
        self._control['cycleniter'] = TextInput( title="cycleniter", value="%s" % self._params['cycleniter'], width=90 )
        self._control['threshold'] = TextInput( title="threshold", value="%s" % self._params['threshold'], width=90 )
        self._control['cycle_factor'] = TextInput( value="%s" % self._params['cyclefactor'], title="cyclefactor", width=90 )


        self._fig['image'] = self._cube.image( height_policy='max', width_policy='max' )
        self._fig['image-source'] = self._cube.js_obj( )

        if image_channels > 1:
            self._control['goto'] = TextInput( title="goto channel", value="", width=90 )
            self._fig['slider'] = self._cube.slider( )
            self._fig['spectra'] = self._cube.spectra( width=450 )

            self._fig['slider'].js_on_change( 'value',
                                              CustomJS( args=dict( flux_src=self._flux_data,
                                                                   residual_src=self._residual_data,
                                                                   threshold_src=self._cyclethreshold_data,
                                                                   convergence_fig=self._fig['convergence'],
                                                                   conv_pipe=self._pipe['converge'], convergence_id=self._convergence_id,
                                                                   img_src=self._fig['image-source'],
                                                                   stopdescmap=ImagingDict.get_summaryminor_stopdesc( ) ),
                                                        code=self._js['update-converge'] + self._js['slider-update'] ) )

            self._control['goto'].js_on_change( 'value', CustomJS( args=dict( img=self._cube.js_obj( ),
                                                                              slider=self._fig['slider'],
                                                                              status=self._status['stopcode'] ),
                                                                   code='''let values = cb_obj.value.split(/[ ,]+/).map((v,) => parseInt(v))
                                                                           if ( values.length > 2 ) {
                                                                             status._error_set = true
                                                                             status.text = '<div>enter at most two indexes</div>'
                                                                           } else if ( values.filter((x) => x < 0 || isNaN(x)).length > 0 ) {
                                                                             status._error_set = true
                                                                             status.text = '<div>invalid channel entered</div>'
                                                                           } else {
                                                                             if ( status._error_set ) {
                                                                               status._error_set = false
                                                                               status.text = '<div/>'
                                                                             }
                                                                             if ( values.length == 1 ) {
                                                                               if ( values[0] >= 0 && values[0] < img.num_chans[1] ) {
                                                                                 status.text= `<div>moving to channel ${values[0]}</div>`
                                                                                 slider.value = values[0]
                                                                               } else {
                                                                                 status._error_set = true
                                                                                 status.text = `<div>channel ${values[0]} out of range</div>`
                                                                               }
                                                                             } else if ( values.length == 2 ) {
                                                                               if ( values[0] < 0 || values[0] >= img.num_chans[1] ) {
                                                                                 status._error_set = true
                                                                                 status.text = `<div>channel ${values[0]} out of range</div>`
                                                                               } else {
                                                                                 if ( values[1] < 0 || values[1] >= img.num_chans[0] ) {
                                                                                   status._error_set = true
                                                                                   status.text = `<div>stokes ${values[1]} out of range</div>`
                                                                                 } else {
                                                                                   status.text= `<div>moving to channel ${values[0]}/${values[1]}</div>`
                                                                                   slider.value = values[0]
                                                                                   img.channel( values[0], values[1] )
                                                                                 }
                                                                               }
                                                                             }
                                                                           }''' ) )
        else:
            self._control['goto'] = None
            self._fig['slider'] = None
            self._fig['spectra'] = None


        self._cb['clean'] = CustomJS( args=dict( btns=self._control['clean'],
                                                 state=dict( mode='interactive', stopped=False, awaiting_stop=False, mask="" ),
                                                 ctrl_pipe=self._pipe['control'], conv_pipe=self._pipe['converge'],
                                                 ids=self._ids['clean'],
                                                 img_src=self._fig['image-source'],
                                                 #spec_src=self._image_spectra,
                                                 niter=self._control['niter'], cycleniter=self._control['cycleniter'],
                                                 nmajor=self._control['nmajor'],
                                                 threshold=self._control['threshold'], cyclefactor=self._control['cycle_factor'],
                                                 flux_src=self._flux_data,
                                                 residual_src=self._residual_data,
                                                 threshold_src=self._cyclethreshold_data,
                                                 convergence_id=self._convergence_id,
                                                 convergence_fig=self._fig['convergence'],
                                                 logbutton=self.__log_button,
                                                 slider=self._fig['slider'],
                                                 image_fig=self._fig['image'],
                                                 spectra_fig=self._fig['spectra'],
                                                 stopstatus=self._status['stopcode'],
                                                 cube_obj = self._cube.js_obj( ),
                                                 go_to = self._control['goto'],
                                                 stopdescmap=ImagingDict.get_summaryminor_stopdesc( ) ),
                                      code=self._js['update-converge'] + self._js['clean-refresh'] + self._js['clean-disable'] +
                                           self._js['clean-enable'] + self._js['clean-status-update'] +
                                           self._js['clean-gui-update'] + self._js['clean-wait'] +
                                           '''function invalid_niter( s ) {
                                                  let v = parseInt( s )
                                                  if ( v > 0 ) return ''
                                                  if ( v == 0 ) return 'niter is zero'
                                                  if ( v < 0 ) return 'niter cannot be negative'
                                                  if ( isNaN(v) ) return 'niter must be an integer'
                                              }
                                              if ( ! state.stopped && cb_obj.origin.name == 'finish' ) {
                                                  let invalid = invalid_niter(niter.value)
                                                  if ( invalid ) update_status( invalid )
                                                  else {
                                                      state.mode = 'continuous'
                                                      update_status( 'Running multiple iterations' )
                                                      disable( false )
                                                      btns['stop'].button_type = "warning"
                                                      ctrl_pipe.send( ids[cb_obj.origin.name],
                                                                      { action: 'finish',
                                                                        value: { niter: niter.value, cycleniter: cycleniter.value, nmajor: nmajor.value,
                                                                                 threshold: threshold.value, cyclefactor: cyclefactor.value,
                                                                                 mask: img_src.masks( ),
                                                                                 breadcrumbs: img_src.breadcrumbs( ) } },
                                                                      update_gui )
                                                  }
                                              }
                                              if ( ! state.stopped && state.mode === 'interactive' &&
                                                   cb_obj.origin.name === 'continue' ) {
                                                  let invalid = invalid_niter(niter.value)
                                                  if ( invalid ) update_status( invalid )
                                                  else {
                                                      update_status( 'Running one set of deconvolution iterations' )
                                                      disable( true )
                                                      // only send message for button that was pressed
                                                      // it's unclear whether 'this.origin.' or 'cb_obj.origin.' should be used
                                                      // (or even if 'XXX.origin.' is public)...
                                                      ctrl_pipe.send( ids[cb_obj.origin.name],
                                                                      { action: 'next',
                                                                        value: { niter: niter.value, cycleniter: cycleniter.value, nmajor: nmajor.value,
                                                                                 threshold: threshold.value, cyclefactor: cyclefactor.value,
                                                                                 mask: img_src.masks( ),
                                                                                 breadcrumbs: img_src.breadcrumbs( ) } },
                                                                      update_gui )
                                                  }
                                              }
                                              if ( state.mode === 'interactive' && cb_obj.origin.name === 'stop' ) {
                                                  disable( true )
                                                  //ctrl_pipe.send( ids[cb_obj.origin.name],
                                                  //                { action: 'stop',
                                                  //                  value: { } },
                                                  //                update_gui )
                                                  flux_src._window_closed = true
                                                  img_src.done( )  /*** <<-------<<<< this will close the tab ***/
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

        mask_color_pick, mask_alpha_pick, mask_clean_notclean_pick = self._cube.bitmask_controls( button_type='light' )

        ###
        ### For cube imaging, tabify the spectrum and convergence plots
        ###
        self._spec_conv_tabs = None
        if self._fig['spectra']:
            self._spec_conv_tabs = Tabs( tabs=[ TabPanel(child=layout([self._fig['convergence']], sizing_mode='stretch_width'), title='Convergence'),
                                                TabPanel(child=layout([self._fig['spectra']], sizing_mode='stretch_width'), title='Spectrum') ],
                                         sizing_mode='stretch_both' )

        self._channel_ctrl = self._cube.channel_ctrl( )

        ### Stokes 'label' should be updated AFTER the channel update has happened
        self._channel_ctrl[1].child.js_on_change( 'label',
                                                  CustomJS( args=dict( img_src=self._fig['image-source'],
                                                                       flux_src=self._flux_data),
                                                            code=self._js['update-converge'] ) )
        self._fig['layout'] = column(
                                  row(
                                      column( row( *self._channel_ctrl, self._cube.coord_ctrl( ),
                                                   Spacer(height=help_button.height, sizing_mode="scale_width"),
                                                   self._cube.palette( ),
                                                   mask_clean_notclean_pick,
                                                   mask_color_pick,
                                                   mask_alpha_pick,
                                                   self.__log_button,
                                                   help_button,
                                                  ),
                                              self._fig['image'],
                                              self._cube.pixel_tracking_text( ),
                                              height_policy='max', width_policy='max',
                                      ),
                                      column( Tabs( tabs=[ TabPanel(child=column( row( self._control['clean']['stop'],
                                                                                       self._control['clean']['continue'],
                                                                                       self._control['clean']['finish'] ),
                                                                                  row( Tip( self._control['nmajor'],
                                                                                            tooltip=Tooltip( content=HTML( 'maximum number of major cycles to run before stopping'),
                                                                                                             position='bottom' ) ),
                                                                                       Tip( self._control['niter'],
                                                                                            tooltip=Tooltip( content=HTML( 'number of clean iterations to run' ),
                                                                                                             position='bottom' ) ),
                                                                                       Tip( self._control['threshold'],
                                                                                            tooltip=Tooltip( content=HTML( 'stopping threshold' ),
                                                                                                             position='bottom' ) ) ),
                                                                                  row( Tip( self._control['goto'],
                                                                                            tooltip=Tooltip( content=HTML( 'to go to a specific channel, <b>enter</b> the channel number and press <b>return</b>' ),
                                                                                                             position='bottom' ) ) if self._fig['slider'] else Div( ),
                                                                                       row( Tip( self._control['cycleniter'],
                                                                                                 tooltip=Tooltip( content=HTML( 'maximum number of <b>minor-cycle</b> iterations' ),
                                                                                                                  position='bottom' ) ),
                                                                                            Tip( self._control['cycle_factor'],
                                                                                                 tooltip=Tooltip( content=HTML( 'scaling on PSF sidelobe level to compute the minor-cycle stopping threshold' ),
                                                                                                                  position='bottom_left' ) ), background="lightgray" ) ),
                                                                                  row ( Div( text="<div><b>status:</b></div>" ), self._status['stopcode'] ) ),
                                                                    title='Iteration' ),
                                                           TabPanel( child=self._cube.colormap_adjust( ),
                                                                     title='Colormap' ),
                                                           TabPanel( child=self._cube.statistics( width=280 ),
                                                                     title='Statistics' ) ],
                                                    sizing_mode='stretch_width' ),
                                              Tip( self._fig['slider'],
                                                   tooltip=Tooltip( content=HTML("slide control to the desired channel"),
                                                                    position="top" ) ) if self._fig['slider'] else Div( ),
                                              height_policy='max', max_width=320
                                      ),
                                      width_policy='max', height_policy='max' ),
                                  row(
                                      self._spec_conv_tabs if self._spec_conv_tabs else self._fig['convergence'],
                                      width_policy='max',
                                  ),
                                  width_policy='max', height_policy='max',
                              )

        self._cube.connect( )

        # Change display type depending on runtime environment
        if self._is_notebook:
            output_notebook()
        else:
            ### Directory is created when an HTTP server is running
            ### (MAX)
###         output_file(self._imagename+'_webpage/index.html')
            pass

        show(self._fig['layout'])

    def __call__( self ):
        '''Display GUI and process events until the user stops the application.

        Example:
            Create ``iclean`` object and display::

                print( "Result: %s" %
                       iclean( vis='refim_point_withline.ms', imagename='test', imsize=512,
                               cell='12.0arcsec', specmode='cube',
                               interpolation='nearest', ... )( ) )
        '''

        self.setup()

        # If Interactive Clean is being run remotely, print helper info for port tunneling
        if self._is_remote:
            # Tunnel ports for Jupyter kernel connection
            print("\nImportant: Copy the following line and run in your local terminal to establish port forwarding.\
                You may need to change the last argument to align with your ssh config.\n")
            print(self._gen_port_fwd_cmd())

            # TODO: Include?
            # VSCode will auto-forward ports that appear in well-formatted addresses.
            # Printing this line will cause VSCode to autoforward the ports
            # print("Cmd: " + str(repr(self.auto_fwd_ports_vscode())))
            input("\nPress enter when port forwarding is setup...")

        async def _run_( ):
            async with self.serve( ) as s:
                await s[0]

        if self._is_notebook:
            ic_task = asyncio.create_task(_run_())
        else:
            asyncio.run(_run_( ))
            return self.result( )

    def setup( self ):
        self.__reset( )
        self._init_pipes()
        self._cube._init_pipes()
        ###
        ### The first time through, reinitialize the mask pixel values if the
        ### user has not supplied a mask...
        ###
        if self._reset_mask_pixels:
            self._reset_mask_pixels = False
            self._cube.set_all_mask_pixels(self._reset_mask_pixels_value)

    @asynccontextmanager
    async def serve( self ):
        '''This function is intended for developers who would like to embed interactive
        clean as a part of a larger GUI. This embedded use of interactive clean is not
        currently supported and would require the addition of parameters to this function
        as well as changes to the interactive clean implementation. However, this function
        does expose the ``asyncio.Future`` that is used to signal completion of the
        interactive cleaning operation, and it provides the coroutines which must be
        managed by asyncio to make the interactive clean GUI responsive.

        Example:
            Create ``iclean`` object, process events and retrieve result::

                ic = iclean( vis='refim_point_withline.ms', imagename='test', imsize=512,
                             cell='12.0arcsec', specmode='cube', interpolation='nearest', ... )
                async def process_events( ):
                    async with ic.serve( ) as state:
                        await state[0]

                asyncio.run(process_events( ))
                print( "Result:", ic.result( ) )


        Returns
        -------
        (asyncio.Future, dictionary of coroutines)
        '''
        def start_http_server():
            import http.server
            import socketserver
            PORT = self._http_port
            DIRECTORY=self._webpage_path

            class Handler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=DIRECTORY, **kwargs)

            with socketserver.TCPServer(("", PORT), Handler) as httpd:
                print("\nServing Interactive Clean webpage from local directory: ", DIRECTORY)
                print("Use Control-C to stop Interactive clean.\n")
                print("Copy and paste one of the below URLs into your browser (Chrome or Firefox) to view:")
                print("http://localhost:"+str(PORT))
                print("http://127.0.0.1:"+str(PORT))

                httpd.serve_forever()

         ###
         ### Launching a webserver allows for remote connecton to the interactive clean running on a remote system
         ### but we need to figure out how we want to manage remote execution.
         ### (MAX)
#        if not self._is_notebook:
#            from threading import Thread
#            thread = Thread(target=start_http_server)
#            thread.daemon = True # Let Ctrl+C kill server thread
#            thread.start()

        self._launch_gui( )

        async with websockets.serve( self._pipe['control'].process_messages, self._pipe['control'].address[0], self._pipe['control'].address[1] ) as ctrl, \
                   websockets.serve( self._pipe['converge'].process_messages, self._pipe['converge'].address[0], self._pipe['converge'].address[1] ) as conv, \
                   self._cube.serve( self.__stop ) as cube:
            self.__result_future = asyncio.Future( )
            yield ( self.__result_future, { 'ctrl': ctrl, 'conv': conv, 'cube': cube } )

    def __retrieve_result( self ):
        '''If InteractiveClean had a return value, it would be filled in as part of the
        GUI dialog between Python and JavaScript and this function would return it'''
        if isinstance(self._error_result,Exception):
            raise self._error_result
        elif self._error_result is not None:
            return self._error_result
        return self._convergence_data

    def result( self ):
        '''If InteractiveClean had a return value, it would be filled in as part of the
        GUI dialog between Python and JavaScript and this function would return it'''
        if self.__result_future is None:
            raise RuntimeError( 'no interactive clean result is available' )
        self._clean.restore( )
        return self.__result_future.result( )

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

    def history( self ):
        '''Retrieves the commands used during the interactive clean session.

        Returns
        -------
        list[str]  tclean calls made during the interactive clean session.
        '''
        return self._clean.cmds( True )
