########################################################################3
#  _gclean.py
#
# Copyright (C) 2021,2022,2023
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
import os
import asyncio
from functools import reduce
import copy
import shutil
import subprocess

###
### import check versions
###
_GCV001 = True
_GCV002 = True
_GCV003 = True
_GCV004 = True

# from casatasks.private.imagerhelpers._gclean import gclean
class gclean:
    '''gclean(...) creates a stream of convergence records which indicate
    the convergence quaility of the tclean process. The initial record
    describes the initial dirty image.
    It is designed for use with the interactive clean GUI, but it could
    be used independently. It can be used as a regular generator:
          for rec in gclean( vis='refim_point_withline.ms', imagename='test', imsize=512, cell='12.0arcsec',
                             specmode='cube', interpolation='nearest', nchan=5, start='1.0GHz', width='0.2GHz',
                             pblimit=-1e-05, deconvolver='hogbom', niter=500, cyclefactor=3, scales=[0, 3, 10] ):
              # use rec to decide when to stop, for example to check stopcode or peak residual:
              # if (rec[0] > 1) or (min(rec[1][0][0]['peakRes']) < 0.001):
              #     break
              print(rec)
    or as an async generator:
          async for rec in gclean( vis='refim_point_withline.ms', imagename='test', imsize=512, cell='12.0arcsec',
                                   specmode='cube', interpolation='nearest', nchan=5, start='1.0GHz', width='0.2GHz',
                                   pblimit=-1e-05, deconvolver='hogbom', niter=500, cyclefactor=3, scales=[0, 3, 10] ):
              # use rec to decide when to stop
              print(rec)


    See also: __next__(...) for a description of the returned rec

    TODO: do we need to preserve any hidden state between tclean calls for the iterbotsink and/or synthesisimager tools?
    '''

    def _tclean( self, *args, **kwargs ):
        """ Calls tclean records the arguments in the local history of tclean calls.

        The full tclean history for this instance can be retrieved via the cmds() method."""
        from casatasks import tclean
        arg_s = ', '.join( map( lambda a: self._history_filter(len(self._exe_cmds), None, repr(a)), args ) )
        kw_s = ', '.join( map( lambda kv: self._history_filter(len(self._exe_cmds), kv[0], "%s=%s" % (kv[0],repr(kv[1]))), kwargs.items()) )
        if len(arg_s) > 0 and len(kw_s) > 0:
            parameters = arg_s + ", " + kw_s
        else:
            parameters = arg_s + kw_s
        self._exe_cmds.append( "tclean( %s )" % parameters )
        self._exe_cmds_per_iter[-1] += 1
        return tclean( *args, **kwargs )

    def _deconvolve( self, *args, **kwargs ):
        """ Calls deconvolve records the arguments in the local history of deconvolve calls.

        The full deconvolve history for this instance can be retrieved via the cmds() method."""
        from casatasks import deconvolve
        arg_s = ', '.join( map( lambda a: self._history_filter(len(self._exe_cmds), None, repr(a)), args ) )
        kw_s = ', '.join( map( lambda kv: self._history_filter(len(self._exe_cmds), kv[0], "%s=%s" % (kv[0],repr(kv[1]))), kwargs.items()) )
        if len(arg_s) > 0 and len(kw_s) > 0:
            parameters = arg_s + ", " + kw_s
        else:
            parameters = arg_s + kw_s
        self._exe_cmds.append( "deconvolve( %s )" % parameters )
        self._exe_cmds_per_iter[-1] += 1
        return deconvolve( *args, **kwargs )

    def __rename_mask( self, new_mask_path ):
        self.__validate_mask( new_mask_path )
        if os.path.exists( new_mask_path ):
            raise RuntimeError( f'''new mask path already exists: {new_mask_path}''' )
        if self._mask != '':
            raise RuntimeError( f'''internal error, mask should not be renamed when it has been supplied by the user: {self._mask}''' )
        if self._effective_mask == '':
            dm = self.__default_mask_name( )
            if not os.path.exists(dm):
                raise RuntimeError( 'no existing mask found, cannot rename' )
            self._effective_mask = dm
        if not os.path.isdir(self._effective_mask):
            raise RuntimeError( f'''existing mask path does not exist or is not a directory: {self._effective_mask}''' )
        os.rename( self._effective_mask, new_mask_path )
        if not os.path.isdir(new_mask_path):
            raise RuntimeError( f'''rename of {self._effective_mask} to {new_mask_path} failed''' )
        self._exe_cmds.append( f'''os.rename( {repr(self._effective_mask)}, {repr(new_mask_path)} )''' )
        self._exe_cmds_per_iter[-1] += 1
        self._effective_mask = new_mask_path

    def _remove_tree( self, directory ):
        if os.path.isdir(directory):
            shutil.rmtree(directory)
            self._exe_cmds.append( f'''shutil.rmtree( {repr(directory)} )''' )
            self._exe_cmds_per_iter[-1] += 1

    def cmds( self, history=False ):
        """ Returns the history of all tclean calls for this instance. If ``history``
        is set to True then the full history will be returned, otherwise the commands
        executed for generating the latest result are returned.
        """
        return self._exe_cmds if history else self._exe_cmds[-self._exe_cmds_per_iter[-1]:]

    def update( self, msg ):
        """ Interactive clean parameters update.

        Args:
            msg: dict with possible keys 'niter', 'cycleniter', 'nmajor', 'threshold', 'cyclefactor' and 'mask'
        """
        if 'niter' in msg:
            try:
                self._niter = int(msg['niter'])
            except ValueError:
                pass
        if 'cycleniter' in msg:
            try:
                self._cycleniter = int(msg['cycleniter'])
            except ValueError:
                pass
        if 'threshold' in msg:
            self._threshold = msg['threshold']
        if 'cyclefactor' in msg:
            try:
                self._cyclefactor = int(msg['cyclefactor'])
            except ValueError:
                pass
        if 'mask' in msg and not os.path.exists( self._effective_mask ):
            ###
            ### the assumption here is that if the _effective_mask exists in the filesystem then
            ### we should not be getting masks provided from the GUI represented as region
            ### specifications (instead the mask changes should be reflected in the mask cube
            ### on disk).
            ###
            self._effective_mask = msg['mask']

    def __init__( self, vis, imagename, field='', spw='', timerange='', uvrange='', antenna='', scan='', observation='', intent='', datacolumn='corrected',
                  imsize=[100], cell=[ ], phasecenter='', stokes='I', startmodel='', specmode='cube', reffreq='', nchan=-1, start='', width='',
                  outframe='LSRK', veltype='radio', restfreq='', interpolation='linear', perchanweightdensity=True, gridder='standard', wprojplanes=int(1),
                  mosweight=True, psterm=False, wbawp=True, conjbeams=False, usepointing=False, pointingoffsetsigdev=[  ], pblimit=0.2, deconvolver='hogbom',
                  smallscalebias=0.0, niter=0, threshold='0.1Jy', nsigma=0.0, cycleniter=-1, nmajor=1, cyclefactor=1.0, scales=[], restoringbeam='', pbcor=False,
                  nterms=int(2), weighting='natural', robust=float(0.5), npixels=0, gain=float(0.1), sidelobethreshold=3.0, noisethreshold=5.0,
                  lownoisethreshold=1.5, negativethreshold=0.0, minbeamfrac=0.3, growiterations=75, dogrowprune=True, minpercentchange=-1.0, fastnoise=True,
                  savemodel='none', usemask='user', mask='', parallel=False, history_filter=lambda index, arg, history_value: history_value ):
        self._vis = vis
        self._imagename = imagename
        self._imsize = imsize
        self._cell = cell
        self._phasecenter = phasecenter
        self._stokes = stokes
        self._startmodel = startmodel
        self._specmode = specmode
        self._reffreq = reffreq
        self._nchan = nchan
        self._start = start
        self._width = width
        self._outframe = outframe
        self._veltype = veltype
        self._restfreq = restfreq
        self._interpolation = interpolation
        self._perchanweightdensity = perchanweightdensity
        self._gridder = gridder
        self._wprojplanes = wprojplanes
        self._mosweight = mosweight
        self._psterm = psterm
        self._wbawp = wbawp
        self._conjbeams = conjbeams
        self._usepointing = usepointing
        self._pointingoffsetsigdev = pointingoffsetsigdev
        self._pblimit = pblimit
        self._deconvolver = deconvolver
        self._smallscalebias = smallscalebias
        self._niter = niter
        self._threshold = threshold
        self._cycleniter = cycleniter
        self._nsigma = nsigma
        self._nmajor = nmajor
        self._cyclefactor = cyclefactor
        self._scales = scales
        self._restoringbeam = restoringbeam
        self._pbcor = pbcor
        self._nterms = nterms
        self._exe_cmds = [ ]
        self._exe_cmds_per_iter = [ ]
        self._history_filter = history_filter
        self._finalized = False
        self._field = field
        self._spw = spw
        self._timerange = timerange
        self._uvrange = uvrange
        self._antenna = antenna
        self._scan = scan
        self._observation = observation
        self._intent = intent
        self._datacolumn = datacolumn
        self._weighting = weighting
        self._robust = robust
        self._npixels = npixels
        self._gain = gain
        self._sidelobethreshold = sidelobethreshold
        self._noisethreshold = noisethreshold
        self._lownoisethreshold = lownoisethreshold
        self._negativethreshold = negativethreshold
        self._minbeamfrac = minbeamfrac
        self._growiterations = growiterations
        self._dogrowprune = dogrowprune
        self._minpercentchange = minpercentchange
        self._fastnoise = fastnoise
        self._savemodel = savemodel
        self._parallel = parallel
        self._usemask = usemask

        ###
        ### 'self._mask' always contains the mask as supplied by the user while 'self._effective_mask' is
        ### the mask currently in play as interactive clean progresses. When the user has supplied a mask,
        ### it should be the same as 'self._mask' but when the mask is managed internally by iclean/gclean
        ### the two will diverge.
        ###
        self._mask = mask

        if self._mask != '':
            ###
            ### If the user supplies a mask that exists on disk, then we need to make sure it does not have
            ### 'tclean's default name because 'tclean' will raise an exception. Further, we should not
            ### modify this mask with the machinations we employ when "self._mask == ''"
            ###
            self.__validate_mask( self._mask )
            self._effective_mask = self._mask
        else:
            ###
            ### If the user supplies '' for the mask, then the mask name must be managed to prevent 'tclean'
            ### from scribbling over our mask (if it were named '<imagename>.mask') while still using the
            ### default mask created on the first run of 'tclean' for subsequent runs of 'tclean'.
            ###
            self._effective_mask = ''

        self._major_done = 0
        self._convergence_result = (None,None,None,{ 'chan': None, 'major': None })
        #                           ^^^^ ^^^^ ^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^----->>> convergence info
        #                              |    | |
        #                              |    | +---------------->>> major cycles done for current run
        #                              |    +------------------>>> tclean stopcode
        #                              +----------------------->>> error message
    @staticmethod
    def __filter_convergence( raw ):
        ###
        ### this function filters out the pieces of the `raw` tclean 'summaryminor'
        ### return dictionary that we care about
        ###
        ### the first index in the `raw` dictionary is the channel axis
        ### each channel may have a number of polarity dictionaries
        ###
        keep_keys = [ 'modelFlux', 'iterDone', 'peakRes', 'stopCode', 'cycleThresh' ]
        ret = {}
        for channel_k,channel_v in raw[0].items( ): # 0: main field in multifield imaging TODO worry about other fields
            ret[channel_k] = {}
            for stokes_k,stokes_v in channel_v.items( ):
                ret[channel_k][stokes_k] = {}
                for summary_k in keep_keys:
                    ret[channel_k][stokes_k][summary_k] = copy.deepcopy(stokes_v[summary_k])
        return ret

    def __add_per_major_items( self, tclean_ret, major_ret, chan_ret ):
        '''Add meta-data about the whole major cycle, including 'cyclethreshold'
        '''
        if 'cyclethreshold' in tclean_ret:
            return dict( major=dict( cyclethreshold=[tclean_ret['cyclethreshold']] if major_ret is None else (major_ret['cyclethreshold'] + [tclean_ret['cyclethreshold']]) ),
                         chan=chan_ret )
        else:
            return dict( major=dict( cyclethreshold=major_ret['cyclethreshold'].append(tclean_ret['cyclethreshold']) ),
                         chan=chan_ret )

    @staticmethod
    def __update_convergence( cumm_sm, new_sm ):
        """Accumulates the per-channel/stokes subimage 'summaryminor' records from new_sm to cumm_sm.
        param cumm_sm: cummulative summary minor records : { chan: { stoke: { key: [values] } } }
        param new_sm: new summary minor records : { chan: { stoke: { key: [values] } } }

        For most "keys", the resultant "values" will be a list, one value per minor cycle.

        The "iterDone" key will be replaced with "iterations", and for the "iterations" key,
        the value in the returned cummulative record will be a rolling sum of iterations done
        for tclean calls so far, one value per minor cycle.
        For example, if there have been two clean calls, and in the first call channel 0 had
        [1] iteration in 1 minor cycle, and for the second call channel 0 had [6, 10, 9, 1]
        iterations in 4 minor cycles), then the resultant "iterations" key for channel 0 would be:
        [1, 7, 17, 26, 27]
        """

        ### substitute 'iterations' for 'iterDone'
        replace_iters_key = lambda x: ('iterations' if x[0] == 'iterDone' else x[0], x[1])
        new_sm = {
            chan_k: {
                stokes_k: {
                    k: v for k,v in map( replace_iters_key, stokes_v.items( ) )
                } for stokes_k,stokes_v in chan_v.items()
            } for chan_k,chan_v in new_sm.items()
        }

        if cumm_sm is None:
            return new_sm
        else:
            def accumulate_tclean_records( cumm_subsm_rec, new_subsm_rec ):
                """
                param cumm_subsm_rec: cummulative subimage 'summaryminor' record : { "key": [minor cycle values,...] }
                param new_subsm_rec: new subimage 'summaryminor' record : { "key": [minor cycle values,...] }
                """
                curr_iters_sum = max(cumm_subsm_rec['iterations']) if 'iterations' in cumm_subsm_rec else 0
                if 'iterations' in new_subsm_rec:
                    iterations_tuple = reduce(  lambda acc, v: (acc[0]+v, acc[1] + [acc[0]+v+curr_iters_sum]),  new_subsm_rec['iterations'],  (0,[])  )
                    new_subsm_rec['iterations'] = iterations_tuple[1] # just want the sum of iterations list
                return { key: cumm_subsm_rec[key] + new_subsm_rec[key] for key in new_subsm_rec.keys( ) }
            return { channel_k: {
                         stokes_k: accumulate_tclean_records( cumm_sm[channel_k][stokes_k], stokes_v )
                         for stokes_k,stokes_v in channel_v.items( ) } for channel_k,channel_v in new_sm.items( )
                   }

    def __next__( self ):
        """ Runs tclean and returns the (stopcode, convergence result) when executed with the python builtin next() function.

        The returned convergence result is a nested dictionary:
        {
            channel id: {
                stokes id: {
                    summary key: [values, one per minor cycle]
                },
            },
        }

        See also: gclean.__update_convergence(...)
        """
        if self._finalized:
            self._convergence_result = ( f'iteration terminated',
                                         self._convergence_result[1],
                                         self._major_done,
                                         self._convergence_result[3] )
            raise StopIteration
        #                                                                             ensure that at least the initial tclean run
        #                      vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv------------>>> is done to produce an initial dirty image
        if self._niter < 1 and self._convergence_result[2] is not None:
            self._convergence_result = ( f'nothing to run, niter == {self._niter}',
                                         self._convergence_result[1],
                                         self._major_done,
                                         self._convergence_result[3] )
            return self._convergence_result
        else:
            ###
            ### CALL SEQUENCE:
            ###       tclean(niter=0),deconvolve(niter=0),tclean(niter=100),deconvolve(niter=0),tclean(niter=100),tclean(niter=0,restoration=True)
            ###
            self._exe_cmds_per_iter.append(0)
            if self._convergence_result[1] is None:
                # initial call to tclean(...) creates the initial dirty image with niter=0
                tclean_ret = self._tclean( vis=self._vis, mask=self._effective_mask, imagename=self._imagename, imsize=self._imsize, cell=self._cell,
                                           phasecenter=self._phasecenter, stokes=self._stokes, startmodel=self._startmodel, specmode=self._specmode,
                                           reffreq=self._reffreq, gridder=self._gridder, wprojplanes=self._wprojplanes, mosweight=self._mosweight,
                                           psterm=self._psterm, wbawp=self._wbawp, conjbeams=self._conjbeams, usepointing=self._usepointing,
                                           interpolation=self._interpolation, perchanweightdensity=self._perchanweightdensity,
                                           nchan=self._nchan, start=self._start, width=self._width, veltype=self._veltype, restfreq=self._restfreq,
                                           outframe=self._outframe, pointingoffsetsigdev=self._pointingoffsetsigdev, pblimit=self._pblimit,
                                           deconvolver=self._deconvolver, smallscalebias=self._smallscalebias, cyclefactor=self._cyclefactor,
                                           scales=self._scales, restoringbeam=self._restoringbeam, pbcor=self._pbcor, nterms=self._nterms,
                                           field=self._field, spw=self._spw, timerange=self._timerange, uvrange=self._uvrange, antenna=self._antenna,
                                           scan=self._scan, observation=self._observation, intent=self._intent, datacolumn=self._datacolumn,
                                           weighting=self._weighting, robust=self._robust, npixels=self._npixels, interactive=False, niter=1,
                                           gain=0.000001, calcres=True, restoration=False, parallel=self._parallel, fullsummary=True )
                if self._mask == '':
                    ### first time through the tclean generated mask is preserved as <imagename>.$pid.mask
                    image_pieces = os.path.splitext(os.path.basename(self._imagename))
                    self.__rename_mask( os.path.join( os.path.dirname(self._imagename), f'{image_pieces[0]}.{os.getpid()}.mask' ) )
                self._deconvolve( imagename=self._imagename, mask=self._effective_mask, niter=0, usemask=self._usemask, restoration=False,
                                  deconvolver=self._deconvolver )
                ### tclean/deconvolve copies the user supplied mask
                if self._mask == '':
                    self._remove_tree(self.__default_mask_name( ))
                self._major_done = 0
            else:
                ### tclean/deconvolve copies the user supplied mask
                if self._mask == '':
                    self._remove_tree(self.__default_mask_name( ))
                tclean_ret = self._tclean( vis=self._vis, mask=self._effective_mask, imagename=self._imagename, imsize=self._imsize, cell=self._cell,
                                           phasecenter=self._phasecenter, stokes=self._stokes, specmode=self._specmode, reffreq=self._reffreq,
                                           gridder=self._gridder, wprojplanes=self._wprojplanes, mosweight=self._mosweight, psterm=self._psterm,
                                           wbawp=self._wbawp, conjbeams=self._conjbeams, usepointing=self._usepointing, interpolation=self._interpolation,
                                           perchanweightdensity=self._perchanweightdensity, nchan=self._nchan, start=self._start,
                                           width=self._width, veltype=self._veltype, restfreq=self._restfreq, outframe=self._outframe,
                                           pointingoffsetsigdev=self._pointingoffsetsigdev, pblimit=self._pblimit, deconvolver=self._deconvolver,
                                           smallscalebias=self._smallscalebias, cyclefactor=self._cyclefactor, scales=self._scales,
                                           restoringbeam=self._restoringbeam, pbcor=self._pbcor, nterms=self._nterms, field=self._field,
                                           spw=self._spw, timerange=self._timerange, uvrange=self._uvrange, antenna=self._antenna,
                                           scan=self._scan, observation=self._observation, intent=self._intent, datacolumn=self._datacolumn,
                                           weighting=self._weighting, robust=self._robust, npixels=self._npixels, interactive=False,
                                           niter=self._niter, restart=True, calcpsf=False, calcres=False, restoration=False, threshold=self._threshold,
                                           nsigma=self._nsigma, cycleniter=self._cycleniter, nmajor=self._nmajor, gain=self._gain,
                                           sidelobethreshold=self._sidelobethreshold, noisethreshold=self._noisethreshold,
                                           lownoisethreshold=self._lownoisethreshold, negativethreshold=self._negativethreshold,
                                           minbeamfrac=self._minbeamfrac, growiterations=self._growiterations, dogrowprune=self._dogrowprune,
                                           minpercentchange=self._minpercentchange, fastnoise=self._fastnoise, savemodel=self._savemodel, maxpsffraction=1,
                                           minpsffraction=0, parallel=self._parallel, fullsummary=True )
                ### tclean/deconvolve copies the user supplied mask
                if self._mask == '':
                    self._remove_tree(self.__default_mask_name( ))
                self._deconvolve( imagename=self._imagename, niter=0, mask=self._effective_mask, usemask=self._usemask, restoration=False,
                                  deconvolver=self._deconvolver )
                ### tclean/deconvolve copies the user supplied mask
                if self._mask == '':
                    self._remove_tree(self.__default_mask_name( ))
                self._major_done = tclean_ret['nmajordone'] if 'nmajordone' in tclean_ret else 0

            if len(tclean_ret) > 0 and 'summaryminor' in tclean_ret and sum(map(len,tclean_ret['summaryminor'].values())) > 0:
                new_summaryminor_rec = gclean.__filter_convergence(tclean_ret['summaryminor'])
                self._convergence_result = ( None,
                                             tclean_ret['stopcode'] if 'stopcode' in tclean_ret else 0,
                                             self._major_done,
                                             self.__add_per_major_items( tclean_ret,
                                                                         self._convergence_result[3]['major'],
                                                                         gclean.__update_convergence( self._convergence_result[3]['chan'],
                                                                                                      new_summaryminor_rec ) ) )
            else:
                self._convergence_result = ( f'tclean returned an empty result',
                                             self._convergence_result[1],
                                             self._major_done,
                                             self._convergence_result[3] )
            return self._convergence_result

    def __reflect_stop( self ):
        ## if python wasn't hacky, you would be able to try/except/raise in lambda
        try:
            return self.__next__( )
        except StopIteration:
            raise StopAsyncIteration

    async def __anext__( self ):
        ### asyncio.run cannot be used here because this is called
        ### within an asyncio loop...
        loop = asyncio.get_event_loop( )
        result = await loop.run_in_executor( None, self.__reflect_stop )
        return result

    def __iter__( self ):
        return self

    def __aiter__( self ):
        return self

    def __split_filename( self, path ):
        return os.path.splitext(os.path.basename(path))

    def __default_mask_name( self ):
        imgparts = self.__split_filename( self._imagename )
        return f'''{imgparts[0]}.mask'''

    def __validate_mask( self, mask_path ):
        if mask_path == self.__default_mask_name( ):
            raise RuntimeError( f'''tclean does not support user supplied mask names like '<imagename>.mask': {mask_path}''' )

    def mask(self):
        return self.__default_mask_name if self._effective_mask == '' else self._effective_mask

    def reset(self):
        #if not self._finalized:
        #    raise RuntimeError('attempt to reset a gclean run that has not been finalized')
        self._finalized = False
        self._convergence_result = ( None,
                                     self._convergence_result[1],
                                     self._major_done,
                                     self._convergence_result[3] )

    def restore(self):
        """ Restores the final image, and returns a path to the restored image. """
        tclean_ret = self._tclean( vis=self._vis, imagename=self._imagename, mask=self._effective_mask, imsize=self._imsize, cell=self._cell,
                                   phasecenter=self._phasecenter, stokes=self._stokes, specmode=self._specmode,
                                   reffreq=self._reffreq, gridder=self._gridder, wprojplanes=self._wprojplanes, mosweight=self._mosweight,
                                   psterm=self._psterm, wbawp=self._wbawp, conjbeams=self._conjbeams, usepointing=self._usepointing,
                                   interpolation=self._interpolation, restfreq=self._restfreq, perchanweightdensity=self._perchanweightdensity, nchan=self._nchan,
                                   start=self._start, width=self._width, outframe=self._outframe, pointingoffsetsigdev=self._pointingoffsetsigdev,
                                   pblimit=self._pblimit, deconvolver=self._deconvolver, cyclefactor=self._cyclefactor, scales=self._scales,
                                   restoringbeam=self._restoringbeam, pbcor=self._pbcor, nterms=self._nterms, field=self._field, spw=self._spw,
                                   timerange=self._timerange, uvrange=self._uvrange, antenna=self._antenna, scan=self._scan,
                                   observation=self._observation, intent=self._intent, datacolumn=self._datacolumn, weighting=self._weighting,
                                   robust=self._robust, npixels=self._npixels, gain=self._gain, sidelobethreshold=self._sidelobethreshold,
                                   noisethreshold=self._noisethreshold, lownoisethreshold=self._lownoisethreshold,
                                   negativethreshold=self._negativethreshold, minbeamfrac=self._minbeamfrac, growiterations=self._growiterations,
                                   dogrowprune=self._dogrowprune, minpercentchange=self._minpercentchange, fastnoise=self._fastnoise,
                                   savemodel=self._savemodel, nsigma=self._nsigma, interactive=False,
                                   niter=0, restart=True, calcpsf=False, calcres=False, restoration=True,
                                   parallel=self._parallel )
        return { "image": f"{self._imagename}.image" }

    def has_next(self):
        return not self._finalized
