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
import os
import copy
import asyncio
import shutil
import websockets
from uuid import uuid4
from bokeh.models import Button, TextInput, Div, Range1d, LinearAxis, CustomJS, Spacer
from bokeh.plotting import ColumnDataSource, figure, show
from bokeh.layouts import column, row, Spacer
from bokeh.io import reset_output as reset_bokeh_output
from ..utils import resource_manager, reset_resource_manager

try:
    ## gclean version number needed for proper interactive clean behavior
    from casatasks.private.imagerhelpers._gclean import _GCV001
    from casatasks.private.imagerhelpers._gclean import gclean as _gclean
except:
    try:
        ###
        ### enable this warning when casa6 a usable _gclean.py (i.e. compatibility is not the default)
        ###
        #print('warning: using tclean compatibility layer...')
        from ..private.compatibility.casatasks.private.imagerhelpers._gclean import _GCV001
        from ..private.compatibility.casatasks.private.imagerhelpers._gclean import gclean as _gclean
    except:
        _gclean = None
        from casagui.utils import warn_import
        warn_import('casatasks')

from casagui.utils import find_ws_address, convert_masks
from casagui.toolbox import CubeMask
from casagui.bokeh.components import SVGIcon
from casagui.bokeh.sources import DataPipe
from ..utils import DocEnum

class MaskMode(DocEnum):
    '''Different masking modes available in addition to a user supplied mask'''
    PB = 1, 'primary beam mask'
    AUTOMT = 2, 'multi-threshold auto masking'

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
        mask (str or MaskMode): user specified CASA imaging mask cube (path) or MaskMode enum indicating
            mask to generate
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
        resource_manager( ).stop_asyncio_loop()
        if self._control_server is not None and self._control_server.ws_server.is_serving( ):
            resource_manager( ).stop_asyncio_loop()
        if self._converge_server is not None and self._converge_server.ws_server.is_serving( ):
            resource_manager( ).stop_asyncio_loop()

    def _abort_handler( self, loop, err ):
        self._error_result = err
        self.__stop( )

    def __reset( self ):
        if self.__pipes_initialized:
            self._pipe = { 'control': None, 'converge': None }
            reset_bokeh_output( )
            reset_resource_manager( )
            self._clean.reset( )

        ###
        ### used by data pipe (websocket) initialization function
        ###
        self.__pipes_initialized = False
        self._mask_history = [ ]

        self._cube = CubeMask( self._residual_path, mask=self._mask_path, abort=self._abort_handler )
        ###
        ### error or exception result
        ###
        self._error_result = None

        ###
        ### websocket servers
        ###
        self._control_server = None
        self._converge_server = None


    def __init__( self, vis, imagename, mask=None, field='', spw='', timerange='', uvrange='', antenna='', scan='', observation='', intent='',
                  datacolumn='corrected', nterms=int(2), imsize=[100], cell=[ ], phasecenter='', stokes='I', startmodel='', specmode='cube', reffreq='',
                  nchan=-1, start='', width='', outframe='LSRK', interpolation='linear', perchanweightdensity=True, gridder='standard', wprojplanes=int(1),
                  mosweight=True, psterm=False, wbawp=True, usepointing=False, conjbeams=False, pointingoffsetsigdev=[  ], pblimit=0.2,
                  deconvolver='hogbom', niter=0, threshold='0.1Jy', nsigma=0.0, cycleniter=-1, cyclefactor=1.0, scales=[], restoringbeam='',
                  pbcor=False, weighting='natural', robust=float(0.5), npixels=0, gain=float(0.1), sidelobethreshold=3.0, noisethreshold=5.0,
                  lownoisethreshold=1.5, negativethreshold=0.0, minbeamfrac=0.3, growiterations=75, dogrowprune=True, minpercentchange=-1.0,
                  fastnoise=True, savemodel='none', parallel=False, nmajor=1 ):

        if deconvolver == 'mtmfs':
            raise RuntimeError("deconvolver task does not support 'mtmf' deconvolver")

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
        ###     if the user has specified a mask cube, it OVERRIDES the default, generated mask name
        self._mask_path = ''
        self._usemask = 'user'
        if isinstance( mask, MaskMode ):
            if mask == MaskMode.AUTOMT:
                self._usemask = 'auto-multithresh'
            elif mask == MaskMode.PB:
                self._usemask = 'pb'
            else:
                raise RuntimeError( 'internal consistence error for MaskMode' )
        elif isinstance( mask, str ) and os.path.isdir( mask ):
            ### override default mask name
            self._mask_path = mask

        ###
        ### clean generator
        ###
        if _gclean is None:
            raise RuntimeError('casatasks gclean interface is not available')

        self._clean = _gclean( vis=vis, imagename=imagename, field=field, spw=spw, timerange=timerange,  uvrange=uvrange, antenna=antenna, scan=scan,
                               observation=observation, intent=intent, datacolumn=datacolumn, nterms=nterms, imsize=imsize, cell=cell,
                               phasecenter=phasecenter, stokes=stokes, startmodel=startmodel, specmode=specmode, reffreq=reffreq, nchan=nchan,
                               start=start, width=width, outframe=outframe, interpolation=interpolation, perchanweightdensity=perchanweightdensity,
                               gridder=gridder, wprojplanes=wprojplanes, mosweight=mosweight, psterm=psterm, wbawp=wbawp, usepointing=usepointing,
                               conjbeams=conjbeams, pointingoffsetsigdev=pointingoffsetsigdev, pblimit=pblimit, deconvolver=deconvolver, niter=niter,
                               threshold=threshold, nsigma=nsigma, cycleniter=cycleniter, cyclefactor=cyclefactor, scales=scales,
                               restoringbeam=restoringbeam, pbcor=pbcor, weighting=weighting, robust=robust, npixels=npixels, gain=gain,
                               sidelobethreshold=sidelobethreshold, noisethreshold=noisethreshold, lownoisethreshold=lownoisethreshold,
                               negativethreshold=negativethreshold, minbeamfrac=minbeamfrac, growiterations=growiterations, dogrowprune=dogrowprune,
                               minpercentchange=minpercentchange, fastnoise=fastnoise, savemodel=savemodel, parallel=parallel, nmajor=nmajor,
                               usemask=self._usemask, mask=self._mask_path
                      )
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

        ###
        ### Initial Conditions
        ###
        self._params = { }
        self._params['nmajor'] = nmajor
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
        if not os.path.isdir(self._mask_path):
            self._mask_path = ("%s.mask" % imagename) if self._clean.has_next() else None
        self._pipe = { 'control': None, 'converge': None }
        self._control = { }
        self._cb = { }
        self._ids = { }
        self._last_mask_breadcrumbs = ''

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
                                               convergence_src._window_closed = false
                                               window.addEventListener( 'beforeunload',
                                                                        function (e) {
                                                                            // if the window is already closed this message is never
                                                                            // delivered (unless interactive clean is called again then
                                                                            // the event shows up in the newly created control pipe
                                                                            if ( convergence_src._window_closed == false ) {
                                                                                ctrl_pipe.send( ids['stop'],
                                                                                                { action: 'stop', value: { } },
                                                                                                  undefined ) } } )
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
                                               if ( clean_msg !== undefined && 'iterdone' in clean_msg ) {
                                                 const remaining = parseInt(niter.value) - parseInt(clean_msg['iterdone'])
                                                 niter.value = '' + (remaining < 0 ? 0 : remaining)
                                               }
                                               img_src.refresh( (data) => { if ( 'stats' in data ) cube_obj.update_statistics( data.stats ) } )

                                               if ( clean_msg !== undefined && 'convergence' in clean_msg ) {
                                                   // save convergence information and update convergence using saved state
                                                   if ( clean_msg.convergence === null ) {
                                                       delete convergence_src._convergence_data
                                                       const pos = img_src.cur_chan
                                                       // fetch convergence information for the current channel (pos[1])
                                                       // ...convergence update expects [ stokes, chan ]
                                                       conv_pipe.send( convergence_id, { action: 'update', value: pos }, update_convergence )
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
                                               nmajor.disabled = true
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
                                               nmajor.disabled = false
                                               niter.disabled = false
                                               cycleniter.disabled = false
                                               threshold.disabled = false
                                               cyclefactor.disabled = false
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
                                               if ( msg.result === 'no-action' ) {
                                                   update_status( 'nothing done' )
                                                   enable( false )
                                               } else
                                               if ( msg.result === 'update' ) {
                                                   if ( 'cmd' in msg ) {
                                                       log.text = log.text + msg.cmd
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
                                                                             value: { niter: niter.value, cycleniter: cycleniter.value, nmajor: nmajor.value,
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

        self._status['log'] = Div( text='''<hr style="width:790px">%s''' % ''.join([ f'<p style="width:790px">{cmd}</p>' for cmd in self._clean.cmds( )[-2:] ]) )
        ###                        >>>--------tclean+deconvolve----------------------------------------------------------------------------------------^^^^^
        self._status['stopcode'] = Div( text="<div>initial image</div>" )

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

                        msg['value']['mask'] = convert_masks(masks=new_mask, coord='pixel', cdesc=self._cube.coorddesc())

                    else:
                        msg['value']['mask'] = ''
                else:
                    msg['value']['mask'] = ''
                self._clean.update( { **msg['value'] } )
                stopcode, self._convergence_data = await self._clean.__anext__( )
                # *******************************************************************************************
                # ******** perhaps the user should not be locked into exiting after the limit is hit ********
                # *******************************************************************************************
                #if stopcode > 1 and stopcode < 9: # 1: iteration limit hit, 9: major cycle limit hit
                #    self._clean.finalize()

                    # self._cube.update_image(self._clean.finalize()['image']) # TODO show the restored image
                if len(self._convergence_data) == 0 and stopcode == 7:
                    return dict( result='error', stopcode=stopcode, cmd=f"<p>mask error encountered (stopcode {stopcode})</p>", convergence=None  )
                if len(self._convergence_data) == 0:
                    return dict( result='no-action', stopcode= stopcode, cmd=f'<p style="width:790px">no operation</p>',
                                 convergence=None, iterdone=0 )
                if len(self._convergence_data) * len(self._convergence_data[0]) > self._threshold_chan or \
                   len(self._convergence_data[0][0]['iterations']) > self._threshold_iterations:
                    return dict( result='update', stopcode=stopcode, cmd=''.join([ f'<p style="width:790px">{cmd}</p>' for cmd in self._clean.cmds( )[-2:] ]),
                                 convergence=None, iterdone=sum([ x['iterations'][1]  for y in self._convergence_data.values() for x in y.values( ) ]) )
                else:
                    return dict( result='update', stopcode=stopcode, cmd=''.join([ f'<p style="width:790px">{cmd}</p>' for cmd in self._clean.cmds( )[-2:] ]),
                                 convergence=self._convergence_data, iterdone=sum([ x['iterations'][1]  for y in self._convergence_data.values() for x in y.values( ) ]) )

                return dict( result='update', stopcode=stopcode, cmd=''.join([ f'<p style="width:790px">{cmd}</p>' for cmd in self._clean.cmds( )[-2:] ]),
                             convergence=self._convergence_data, iterdone=sum([ x['iterations'][1]  for y in self._convergence_data.values() for x in y.values( ) ]) )
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

        self._fig['convergence'] = figure( tooltips=[ ("x","$x"), ("y","$y"), ("value", "(@peakRes, @modelFlux)")],
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


        self._control['nmajor'] = TextInput( title='nmajor', value="%s" % self._params['nmajor'], width=90 )
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
                                                 nmajor=self._control['nmajor'],
                                                 threshold=self._control['threshold'], cyclefactor=self._control['cycle_factor'],
                                                 convergence_src=self._convergence_source, convergence_id=self._convergence_id,
                                                 convergence_fig=self._fig['convergence'],
                                                 log=self._status['log'],
                                                 slider=self._fig['slider'],
                                                 image_fig=self._fig['image'],
                                                 spectra_fig=self._fig['spectra'],
                                                 stopstatus=self._status['stopcode'],
                                                 cube_obj = self._cube.js_obj( )
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
                                                                    value: { niter: niter.value, cycleniter: cycleniter.value, nmajor: nmajor.value,
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
                                                                    value: { niter: niter.value, cycleniter: cycleniter.value, nmajor: nmajor.value,
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
                                                  convergence_src._window_closed = true
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

        self._fig['slider'].js_on_change( 'value',
                                          CustomJS( args=dict( convergence_src=self._convergence_source,
                                                               convergence_fig=self._fig['convergence'],
                                                               conv_pipe=self._pipe['converge'], convergence_id=self._convergence_id,
                                                               img_src=self._fig['image-source']
                                                             ),
                                                    code='''const pos = img_src.cur_chan;''' +             ### later we will receive the polarity from some widget mechanism...
                                                            self._js['update-converge'] + self._js['slider-update'] ) )

        # Generates the HTML for the controls layout:
        # nmajor niter cycleniter cycle_factor threshold  -----------
        #                  slider                         -  image  -    help
        # goto    continue finish stop                    -----------    help
        # status: stopcode                                               help
        # stats                                                          help
        # spectra
        # convergence
        # log

        mask_color_pick, mask_alpha_pick, mask_clean_notclean_pick = self._cube.bitmask_controls( )

        self._fig['layout'] = column(
                                  row(
                                      column(
                                          row( self._control['nmajor'],
                                               self._control['niter'],
                                               Spacer(width=10, sizing_mode='scale_height'),
                                               self._control['clean']['continue'],
                                               self._control['clean']['finish'] ),
                                          row( self._control['cycleniter'],
                                               self._control['cycle_factor'],
                                               self._control['threshold'],
                                               self._control['clean']['stop'] ),
                                          row( self._fig['slider'], self._control['goto'] ),
                                          row ( Div( text="<div><b>status:</b></div>" ), self._status['stopcode'] ),
                                          self._cube.statistics( sizing_mode = "stretch_height" ),
                                      ),
                                      column( self._fig['image'],
                                              row( Spacer(height=self._control['help'].height, sizing_mode="scale_width"),
                                                   self._cube.palette( ),
                                                   mask_clean_notclean_pick,
                                                   mask_color_pick,
                                                   mask_alpha_pick,
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
        self._cube.connect( )
        show(self._fig['layout'])

    def _asyncio_loop( self ):
        async def async_loop( f1, f2, f3 ):
            return await asyncio.gather( f1, f2, f3 )

        self._control_server = websockets.serve( self._pipe['control'].process_messages, self._pipe['control'].address[0], self._pipe['control'].address[1] )
        self._converge_server = websockets.serve( self._pipe['converge'].process_messages, self._pipe['converge'].address[0], self._pipe['converge'].address[1] )
        resource_manager( ).reg_webserver(self._control_server.ws_server)
        resource_manager( ).reg_webserver(self._converge_server.ws_server)
        return async_loop( self._control_server, self._converge_server, self._cube.loop( ) )

    def __call__( self, loop=asyncio.new_event_loop( ) ):
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
        ###
        ### new event loops must be set in asyncio to become active
        ###
        if loop != asyncio.get_event_loop( ):
            asyncio.set_event_loop(loop)

        self.__reset( )

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

    def history( self ):
        '''Retrieves the commands used during the interactive clean session.

        Returns
        -------
        list[str]  tclean calls made during the interactive clean session.
        '''
        return self._clean.cmds( )
