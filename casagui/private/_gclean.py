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
#        Internet email: casa-feedback@nrao.edu.
#        Postal address: AIPS++ Project Office
#                        National Radio Astronomy Observatory
#                        520 Edgemont Road
#                        Charlottesville, VA 22903-2475 USA
#
import os
import asyncio
from functools import reduce
import copy
import numpy as np
import shutil
import time
import subprocess

from casatasks.private.imagerhelpers.imager_return_dict import ImagingDict
from casatasks import deconvolve, tclean, imstat
from casatasks import casalog

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
        arg_s = ', '.join( map( lambda a: self._history_filter(len(self._exe_cmds), None, repr(a)), args ) )
        kw_s = ', '.join( map( lambda kv: self._history_filter(len(self._exe_cmds), kv[0], "%s=%s" % (kv[0],repr(kv[1]))), kwargs.items()) )
        if len(arg_s) > 0 and len(kw_s) > 0:
            parameters = arg_s + ", " + kw_s
        else:
            parameters = arg_s + kw_s
        self._exe_cmds.append( "deconvolve( %s )" % parameters )
        self._exe_cmds_per_iter[-1] += 1
        return deconvolve( *args, **kwargs )

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

        if history:
            return self._exe_cmds
        else:
            if self._exe_cmds_per_iter[-1] > 0:
                # Return the last N commands
                return self._exe_cmds[-self._exe_cmds_per_iter[-1]:]
            else:
                # If convergence is hit, no commands were run so return nothing
                return []


    def update( self, msg ):
        """ Interactive clean parameters update.

        Args:
            msg: dict with possible keys 'niter', 'cycleniter', 'nmajor', 'threshold', 'cyclefactor'

        Returns:
            stopcode : Stop code in case of error (-1 on error, 0 if no error), int
            stopdesc : Exception error message, str
        """
        if 'niter' in msg:
            try:
                self._niter = int(msg['niter'])
                if self._niter < -1:
                    return -1, f"niter must be >= -1"
            except ValueError as err:
                return -1, "niter must be an integer"

        if 'cycleniter' in msg:
            try:
                self._cycleniter = int(msg['cycleniter'])
                if self._cycleniter < -1:
                    return -1, f"cycleniter must be >= -1"
            except ValueError:
                return -1, "cycleniter must be an integer"

        if 'nmajor' in msg:
            try:
                self._nmajor = int(msg['nmajor'])
                if self._nmajor < -1:
                    return -1, f"nmajor must be >= -1"
            except ValueError as e:
                return -1, "nmajor must be an integer"

        if 'threshold' in msg:
            try:
                self._threshold = float(msg['threshold'])
                if self._threshold < 0:
                    return -1, f"threshold must be >= 0"
            except ValueError:
                if isinstance(msg['threshold'], str) and "jy" in msg['threshold'].lower():
                    self._threshold_to_float(msg['threshold']) # Convert str to float
                else:
                    return -1, f"threshold must be a number, or a number with units (Jy/mJy/uJy)"


        if 'nsigma' in msg:
            try:
                self._nsigma = float(msg['nsigma'])
                if self._nsigma < 0:
                    return -1, f"nsigma must be >= 0"
            except ValueError:
                return -1, "nsigma must be a number"


        if 'gain' in msg:
            try:
                self._gain = float(msg['gain'])
                if self._gain <= 0:
                    return -1, f"gain must be > 0"
            except ValueError:
                return -1, "gain must be a number"


        if 'cyclefactor' in msg:
            try:
                self._cyclefactor = float(msg['cyclefactor'])
                if self._cyclefactor <= 0:
                    return -1, f"cyclefactor must be > 0"
            except ValueError:
                return -1, "cyclefactor must be a number"

        ### Automasking parameters

        if 'dogrowprune' in msg:
            try:
                self._dogrowprune = bool(msg['dogrowprune'])
            except ValueError:
                return -1, "dogrowprune must be a boolean"

        if 'noisethreshold' in msg:
            try:
                self._noisethreshold = float(msg['noisethreshold'])
                if self._noisethreshold < 0:
                    return -1, f"noisethreshold must be >= 0"
            except ValueError:
                return -1, "noisethreshold must be a number"

        if 'sidelobethreshold' in msg:
            try:
                self._sidelobethreshold = float(msg['sidelobethreshold'])
                if self._sidelobethreshold < 0:
                    return -1, f"sidelobethreshold must be >= 0"
            except ValueError:
                return -1, "sidelobethreshold must be a number"

        if 'lownoisethreshold' in msg:
            try:
                self._lownoisethreshold = float(msg['lownoisethreshold'])
                if self._lownoisethreshold < 0:
                    return -1, f"lownoisethreshold must be >= 0"
            except ValueError:
                return -1, "lownoisethreshold must be a number"

        if 'minbeamfrac' in msg:
            try:
                self._minbeamfrac = float(msg['minbeamfrac'])
                if self._minbeamfrac < 0:
                    return -1, f"minbeamfrac must be >= 0"
            except ValueError:
                return -1, "minbeamfrac must be a number"

        if 'negativethreshold' in msg:
            try:
                self._negativethreshold = float(msg['negativethreshold'])
                if self._negativethreshold < 0:
                    return -1, f"negativethreshold must be >= 0"
            except ValueError:
                return -1, "negativethreshold must be a number"



        return 0, ""



    def _threshold_to_float(self, msg=None):
        # Convert threshold from string to float if necessary
        if msg is not None:
            if isinstance(msg, str):
                if "mJy" in msg:
                    self._threshold = float(msg.replace("mJy", "")) / 1e3
                elif "uJy" in msg:
                    self._threshold = float(msg.replace("uJy", "")) / 1e6
                elif "Jy" in msg:
                    self._threshold = float(msg.replace("Jy", ""))
        else:
            if isinstance(self._threshold, str):
                if "mJy" in self._threshold:
                    self._threshold = float(self._threshold.replace("mJy", "")) / 1e3
                elif "uJy" in self._threshold:
                    self._threshold = float(self._threshold.replace("uJy", "")) / 1e6
                elif "Jy" in self._threshold:
                    self._threshold = float(self._threshold.replace("Jy", ""))


    def __init__(self, vis, imagename, selectdata=True, field='', spw='', timerange='', uvrange='', antenna='', scan='', observation='', intent='', datacolumn='corrected', imsize=[100], cell=[ ],
                 phasecenter='', projection='SIN', stokes='I', startmodel='', specmode='cube', reffreq='', nchan=-1, start='', width='', outframe='LSRK', veltype='radio', restfreq='',
                 interpolation='linear', perchanweightdensity=True, gridder='standard', facets=int(1), psfphasecenter='', wprojplanes=int(1), mosweight=True, aterm=True, psterm=False, wbawp=True,
                 conjbeams=False, usepointing=False, cfcache = '', pointingoffsetsigdev=[  ], vptable='', computepastep=float(360.0), rotatepastep=float(360.0), pblimit=0.2, normtype='flatnoise',
                 deconvolver='hogbom', smallscalebias=0.0, fusedthreshold=0, largestscale=-1, niter=0, threshold='0.1Jy', nsigma=0.0, cycleniter=-1, nmajor=1, cyclefactor=1.0, minpsffraction=0.05,
                 maxpsffraction=0.8, scales=[], restoringbeam='', pbcor=False, outlierfile='', nterms=int(2), weighting='natural', robust=float(0.5), noise='0.0Jy', uvtaper=[], npixels=0,
                 gain=float(0.1), pbmask=0.2, sidelobethreshold=3.0, noisethreshold=5.0, lownoisethreshold=1.5, negativethreshold=0.0, smoothfactor=float(1.0), minbeamfrac=0.3, cutthreshold=0.01,
                 growiterations=75, dogrowprune=True, minpercentchange=-1.0, verbose=False, fastnoise=True, savemodel='none', usemask='user', mask='', restoration=True, restart=True, calcres=True,
                 calcpsf=True, psfcutoff=float(0.35), parallel=False, history_filter=lambda index, arg, history_value: history_value ):

        self._vis = vis
        self._imagename = imagename
        self._selectdata = selectdata
        self._imsize = imsize
        self._cell = cell
        self._phasecenter = phasecenter
        self._projection = projection
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
        self._facets = facets
        self._psfphasecenter = psfphasecenter
        self._wprojplanes = wprojplanes
        self._mosweight = mosweight
        self._aterm = aterm
        self._psterm = psterm
        self._wbawp = wbawp
        self._conjbeams = conjbeams
        self._usepointing = usepointing
        self._cfcache = cfcache
        self._pointingoffsetsigdev = pointingoffsetsigdev
        self._vpable = vptable
        self._computepastep = computepastep
        self._rotatepastep = rotatepastep
        self._pblimit = pblimit
        self._normtype = normtype
        self._deconvolver = deconvolver
        self._smallscalebias = smallscalebias
        self._fusedthreshold = fusedthreshold
        self._largestscale = largestscale
        self._niter = niter
        self._threshold = threshold
        self._cycleniter = cycleniter
        self._minpsffraction = minpsffraction
        self._maxpsffraction = maxpsffraction
        self._nsigma = nsigma
        self._nmajor = nmajor
        self._cyclefactor = cyclefactor
        self._scales = scales
        self._restoringbeam = restoringbeam
        self._pbcor = pbcor
        #self._outlierfile = outlierfile
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
        self._noise = noise
        self._uvtaper = uvtaper
        self._npixels = npixels
        self._gain = gain
        self._pbmask = pbmask
        self._sidelobethreshold = sidelobethreshold
        self._noisethreshold = noisethreshold
        self._lownoisethreshold = lownoisethreshold
        self._negativethreshold = negativethreshold
        self._smoothfactor = smoothfactor
        self._minbeamfrac = minbeamfrac
        self._cutthreshold = cutthreshold
        self._growiterations = growiterations
        self._dogrowprune = dogrowprune
        self._minpercentchange = minpercentchange
        self._verbose = verbose
        self._fastnoise = fastnoise
        self._savemodel = savemodel
        self._parallel = parallel
        self._usemask = usemask
        self._mask = mask
        self._restoration = restoration
        self._restart = restart
        self._calcres = calcres
        self._calcpsf = calcpsf
        self._psfcutoff = psfcutoff
        self.global_imdict = ImagingDict()
        self.current_imdict = ImagingDict()
        self._major_done = 0
        self.hasit = False # Convergence flag
        self._has_restored = False
        self.stopdescription = '' # Convergence flag
        self._initial_mask_exists = False
        self._convergence_result = (None,None,None,None,None,{ 'chan': None, 'major': None })
        #                           ^^^^ ^^^^ ^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^----->>> convergence info
        #                              |    | |     |    +----->>> Number of global iterations remaining for current run (niterleft)
        #                              |    | |     +---------->>> Number of major cycles remaining for current run (nmajorleft)
        #                              |    | +---------------->>> major cycles done for current run (nmajordone)
        #                              |    +------------------>>> tclean stopcode
        #                              +----------------------->>> tclean stopdescription

        # Convert threshold from string to float, interpreting units.
        # XXX : We should ideally use quantities, but we are trying to
        # stick to "public API" funtions inside _gclean
        self._threshold_to_float()


    def __add_per_major_items( self, tclean_ret, major_ret, chan_ret ):
        '''Add meta-data about the whole major cycle, including 'cyclethreshold'
        '''

        if 'cyclethreshold' in tclean_ret:

            rdict = dict( major=dict( cyclethreshold=[tclean_ret['cyclethreshold']] if major_ret is None else (major_ret['cyclethreshold'] + [tclean_ret['cyclethreshold']]) ),
                         chan=chan_ret )
        else:
            rdict = dict( major=dict( cyclethreshold=major_ret['cyclethreshold'].append(tclean_ret['cyclethreshold']) ),
                         chan=chan_ret )

        return rdict


    def _calc_deconv_controls(self, imdict, niterleft=0, threshold=0, cycleniter=-1):
        """
        Calculate cycleniter and cyclethreshold for deconvolution.
        """

        use_cycleniter = niterleft  #niter - imdict.returndict['iterdone']

        if cycleniter > -1 : # User is forcing this number
            use_cycleniter = min(cycleniter, use_cycleniter)

        psffrac = imdict.returndict['maxpsfsidelobe'] * self._cyclefactor
        psffrac = max(psffrac, self._minpsffraction)
        psffrac = min(psffrac, self._maxpsffraction)

        # TODO : This assumes the default field (i.e., field=0);
        # This won't work for multiple fields.
        cyclethreshold = psffrac * imdict.get_peakres()
        cyclethreshold = max(cyclethreshold, threshold)

        return int(use_cycleniter), cyclethreshold


    def __update_convergence(self):
        """
        Accumulates the per-channel/stokes summaryminor keys across all major cycle calls so far.

        The "iterDone" key will be replaced with "iterations", and for the "iterations" key,
        the value in the returned cummulative record will be a rolling sum of iterations done
        for tclean calls so far, one value per minor cycle.
        For example, if there have been two clean calls, and in the first call channel 0 had
        [1] iteration in 1 minor cycle, and for the second call channel 0 had [6, 10, 9, 1]
        iterations in 4 minor cycles), then the resultant "iterations" key for channel 0 would be:
        [1, 7, 17, 26, 27]
        """

        keys = ['modelFlux', 'iterDone', 'peakRes', 'stopCode', 'cycleThresh']

        # Grab tuples of keys of interest
        outrec = {}
        for nn in range(self.global_imdict.nchan):
            outrec[nn] = {}
            for ss in range(self.global_imdict.nstokes):
                outrec[nn][ss] = {}
                for key in keys:
                    # Replace iterDone with iterations
                    if key == 'iterDone':
                        # Maintain cumulative sum of iterations per entry
                        outrec[nn][ss]['iterations'] = np.cumsum(self.global_imdict.get_key(key, stokes=ss, chan=nn))
                        # Replace iterDone with iterations
                        #outrec[nn][ss]['iterations'] =  self.global_imdict.get_key(key, stokes=ss, chan=nn)
                    else:
                        outrec[nn][ss][key] = self.global_imdict.get_key(key, stokes=ss, chan=nn)

        return outrec


    def _check_initial_mask(self):
        """
        Check if a mask from a previous run exists on disk or not.
        """

        if self._usemask == 'user' and self._mask == '':
            maskname = self._imagename + '.mask'

            if os.path.exists(maskname):
                self._initial_mask_exists = True
            else:
                self._initial_mask_exists = False

    def _fix_initial_mask(self):
        """
        If on start up, no user mask is provided, then flip the initial mask to
        be all zeros for interactive use.
        """

        from casatools import image
        ia = image()

        if self._usemask == 'user' and self._mask == '':
            maskname = self._imagename + '.mask'

            # This means the mask was newly created by deconvolve, so flip it
            if os.path.exists(maskname) and self._initial_mask_exists is False:
                ia.open(maskname)
                ia.set(0.0)
                ia.close()

    def _update_peakres(self):
        if self._deconvolver == 'mtmfs':
            residname = self._imagename + '.residual.tt0'
        else:
            residname = self._imagename + '.residual'

        maskname = self._imagename + '.mask'
        if not os.path.exists(maskname):
            maskname = ''

        peakres = imstat(imagename=residname, mask=f'''"{maskname}"''')['max']
        if len(maskname) > 0:
            masksum = imstat(imagename=maskname)['sum']
        else:
            masksum = []

        if len(peakres) > 0:
            peakres = peakres[0]
        else:
            peakres = None

        if len(masksum) > 0:
            masksum = masksum[0]
        else:
            masksum = None

        return peakres, masksum

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

        tclean_ret = {}
        deconv_ret = {}

        #                      vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv------------>>> is done to produce an initial dirty image
        if self._niter < 1 and self._convergence_result[2] is not None:
            self._convergence_result = ( f'nothing to run, niter == {self._niter}',
                                         self._convergence_result[1],
                                         self._major_done,
                                         self._nmajor,
                                         self._niter,
                                         self._convergence_result[5] )
            return self._convergence_result
        else:
            ### CALL SEQUENCE:
            ###       tclean(niter=0),deconvolve(niter=0),tclean(niter=100),deconvolve(niter=0),tclean(niter=100),tclean(niter=0,restoration=True)
            self._exe_cmds_per_iter.append(0)
            try:
                if self._convergence_result[1] is None:
                    # initial call to tclean(...) creates the initial dirty image with niter=0

                    # If calcres and calcpsf are False, no need to run initial tclean - assume image products already on disk.
                    if not (self._calcres == False and self._calcpsf == False):
                        casalog.post('Running initial major cycle to create first residual image.', 'INFO')
                        print('Running initial major cycle to create first residual image.')
                        tclean_ret = self._tclean( vis=self._vis, mask=self._mask, imagename=self._imagename, imsize=self._imsize, cell=self._cell, selectdata=self._selectdata, phasecenter=self._phasecenter, stokes=self._stokes,
                                              startmodel=self._startmodel, specmode=self._specmode, projection=self._projection, reffreq=self._reffreq, gridder=self._gridder, wprojplanes=self._wprojplanes, facets=self._facets,
                                              mosweight=self._mosweight, psfphasecenter = self._psfphasecenter, aterm=self._aterm, psterm=self._psterm, wbawp=self._wbawp, conjbeams=self._conjbeams, cfcache=self._cfcache,
                                              usepointing=self._usepointing, computepastep=self._computepastep, rotatepastep=self._rotatepastep, normtype=self._normtype, fusedthreshold=self._fusedthreshold,
                                              largestscale=self._largestscale, noise = self._noise, uvtaper=self._uvtaper, psfcutoff=self._psfcutoff, interpolation=self._interpolation,
                                              perchanweightdensity=self._perchanweightdensity, nchan=self._nchan, start=self._start, width=self._width, veltype=self._veltype, restfreq=self._restfreq, outframe=self._outframe,
                                              pointingoffsetsigdev=self._pointingoffsetsigdev, pblimit=self._pblimit, deconvolver=self._deconvolver, smallscalebias=self._smallscalebias, cyclefactor=self._cyclefactor,
                                              scales=self._scales, restoringbeam=self._restoringbeam, pbcor=self._pbcor, nterms=self._nterms, field=self._field, spw=self._spw, timerange=self._timerange, uvrange=self._uvrange,
                                              antenna=self._antenna, scan=self._scan, observation=self._observation, intent=self._intent, datacolumn=self._datacolumn, weighting=self._weighting, robust=self._robust,
                                              npixels=self._npixels, interactive=False, niter=0, gain=self._gain, calcres=self._calcres, calcpsf=self._calcpsf, restoration=False, parallel=self._parallel, fullsummary=True)
                                              # outlierfile = self._outlierfile,

                    # Check if a mask from a previous run exists on disk
                    self._check_initial_mask()

                    deconv_ret = self._deconvolve(imagename=self._imagename, startmodel=self._startmodel,
                                                  deconvolver=self._deconvolver, scales=self._scales, nterms=self._nterms,
                                                  smallscalebias=self._smallscalebias, restoration=False, restoringbeam=self._restoringbeam,
                                                  niter = 0, gain=self._gain, threshold=self._threshold, nsigma=self._nsigma,
                                                  interactive = False, fullsummary=True, fastnoise=self._fastnoise, usemask=self._usemask,
                                                  mask = self._mask, pbmask=self._pbmask, sidelobethreshold=self._sidelobethreshold,
                                                  noisethreshold=self._noisethreshold, lownoisethreshold=self._lownoisethreshold,
                                                  negativethreshold=self._negativethreshold, smoothfactor=self._smoothfactor,
                                                  minbeamfrac=self._minbeamfrac, cutthreshold=self._cutthreshold,
                                                  growiterations=self._growiterations, dogrowprune=self._dogrowprune,
                                                  verbose=self._verbose)

                    # If no mask from a previous run exists, over-write the ones with zeros for the default mask
                    self._fix_initial_mask()


                    if len(tclean_ret) > 0 and len(deconv_ret) > 0:
                        self.current_imdict.returndict = self.current_imdict.merge(tclean_ret, deconv_ret)
                    elif len(tclean_ret) > 0 and len(deconv_ret) == 0:
                        self.current_imdict.returndict = copy.deepcopy(tclean_ret)
                    elif len(tclean_ret) == 0 and len(deconv_ret) > 0:
                        self.current_imdict.returndict = copy.deepcopy(deconv_ret)
                    else: # Both dicts are empty, this should never happen
                        raise ValueError("Both tclean and deconvolve return dicts are empty. This should never happen.")

                    self.global_imdict.returndict = self.current_imdict.returndict

                    ## Initial call where niterleft and nmajorleft are same as original input values.
                    self.hasit, self.stopdescription = self.global_imdict.has_converged(self._niter, self._threshold, self._nmajor)

                    self.current_imdict.returndict['stopcode'] = self.hasit
                    self.current_imdict.returndict['stopDescription'] = self.stopdescription
                    self._major_done = 0
                else:
                    # Reset convergence every time, since we return control to the GUI after a single major cycle
                    self.current_imdict.returndict['iterdone'] = 0.

                    # Mask can be updated here...
                    # Check for mask update - peakres + masksum
                    _peakres, _masksum = self._update_peakres()

                    self.hasit, self.stopdescription = self.global_imdict.has_converged(self._niter, self._threshold, self._nmajor, masksum=_masksum, peakres=_peakres)

                    #self.global_imdict.returndict['stopcode'] = self.hasit
                    #self.global_imdict.returndict['stopDescription'] = self.stopdescription

                    #self.current_imdict.returndict['stopcode'] = self.hasit
                    #self.current_imdict.returndict['stopDescription'] = self.stopdescription

                    # Has not, i.e., not converged
                    if self.hasit ==0 :
                        use_cycleniter, cyclethreshold = self._calc_deconv_controls(self.current_imdict, self._niter, self._threshold, self._cycleniter)

                        # Run the minor cycle
                        deconv_ret = self._deconvolve(imagename=self._imagename, startmodel=self._startmodel,
                                                  deconvolver=self._deconvolver, restoration=False,
                                                  threshold=cyclethreshold, niter=use_cycleniter, gain=self._gain, fullsummary=True)

                        # Run the major cycle
                        tclean_ret = self._tclean( vis=self._vis, imagename=self._imagename, imsize=self._imsize, cell=self._cell,
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
                                           niter=0, restart=True, calcpsf=False, calcres=True, restoration=False, threshold=self._threshold,
                                           nsigma=self._nsigma, cycleniter=self._cycleniter, nmajor=1, gain=self._gain,
                                           sidelobethreshold=self._sidelobethreshold, noisethreshold=self._noisethreshold,
                                           lownoisethreshold=self._lownoisethreshold, negativethreshold=self._negativethreshold,
                                           minbeamfrac=self._minbeamfrac, growiterations=self._growiterations, dogrowprune=self._dogrowprune,
                                           minpercentchange=self._minpercentchange, fastnoise=self._fastnoise, savemodel=self._savemodel,
                                           maxpsffraction=self._maxpsffraction,
                                           minpsffraction=self._minpsffraction, parallel=self._parallel, fullsummary=True )

                        # Replace return dict with new return dict
                        # The order of the dicts into merge is important.
                        self.current_imdict.returndict = self.current_imdict.merge(tclean_ret, deconv_ret)

                        # Append new return dict to global return dict
                        self.global_imdict.returndict = self.global_imdict.concat(self.global_imdict.returndict, self.current_imdict.returndict)
                        self._major_done = self.current_imdict.returndict['nmajordone']

                        ## Decrement count for the major cycle just done...
                        self.__decrement_counts()

                        cycleniterleft = self._cycleniter - self.current_imdict.returndict['iterdone']

                        # Use global imdict for convergence check
                        if deconv_ret['stopcode'] == 7:   ## Tell the convergence checker that the mask is zero and iterations were skipped
                            self.hasit, self.stopdescription = self.global_imdict.has_converged(self._niter, self._threshold, self._nmajor, masksum=0)
                        else:
                            self.hasit, self.stopdescription = self.global_imdict.has_converged(self._niter, self._threshold, self._nmajor, cycleniter=cycleniterleft)


                    self.global_imdict.returndict['stopcode'] = self.hasit
                    self.global_imdict.returndict['stopDescription'] = self.stopdescription

                    if not self.hasit and self._usemask == 'auto-multithresh':
                        # If we haven't converged, run deconvolve to update the mask
                        # Note : This is only necessary if using auto-multithresh. If using the interactive viewer to draw, the mask gets updated as the regions
                        # are added or removed in the interactive viewer.
                        self._deconvolve(imagename=self._imagename, startmodel=self._startmodel, deconvolver=self._deconvolver, restoration=False, threshold=self._threshold, niter=0,
                                         nsigma=self._nsigma, fullsummary=True, fastnoise=self._fastnoise, usemask=self._usemask, mask='', pbmask=self._pbmask,
                                         sidelobethreshold=self._sidelobethreshold, noisethreshold=self._noisethreshold, lownoisethreshold=self._lownoisethreshold,
                                         negativethreshold=self._negativethreshold, smoothfactor=self._smoothfactor, minbeamfrac=self._minbeamfrac, cutthreshold=self._cutthreshold,
                                         growiterations=self._growiterations, dogrowprune=self._dogrowprune, verbose=self._verbose)


                if len(self.global_imdict.returndict) > 0 and 'summaryminor' in self.global_imdict.returndict and sum(map(len,self.global_imdict.returndict['summaryminor'].values())) > 0:
                    self._convergence_result = ( self.global_imdict.returndict['stopDescription'] if 'stopDescription' in self.global_imdict.returndict else '',
                                                 self.global_imdict.returndict['stopcode'] if 'stopcode' in self.global_imdict.returndict else 0,
                                                 self._major_done,
                                                 self._nmajor,
                                                 self._niter,
                                                 self.__add_per_major_items( self.global_imdict.returndict,
                                                                             self._convergence_result[5]['major'],
                                                                             self.__update_convergence()))
                else:
                    self._convergence_result = ( f'tclean returned an empty result',
                                                 self._convergence_result[1],
                                                 self._major_done,
                                                 self._nmajor,
                                                 self._niter,
                                                 self._convergence_result[5] )
            except Exception as e:
                self._convergence_result = ( str(e),
                                             -1,
                                             self._major_done,
                                             self._nmajor,
                                             self._niter,
                                             self._convergence_result[5] )
                return self._convergence_result

            return self._convergence_result

    def __decrement_counts( self ):
        ## Update niterleft and nmajorleft now.
        if self.hasit == 0:  ##If not yet converged.
            if self._nmajor != -1:   ## If -1, don't touch it.
                self._nmajor = self._nmajor - 1
                if self._nmajor<0:   ## Force a floor
                    self._nmajor=0
            self._niter = self._niter - self.current_imdict.get_key('iterdone')
            if self._niter<0:  ## This can happen when we're counting niter across channels in a single minor cycle set, and it crosses the total.
                self._niter=0  ## Force a floor
        else:
            return  ##If convergence has been reached, don't try to decrement further.


    def __reflect_stop( self ):
        ## if python wasn't hacky, you would be able to try/except/raise in lambda
        time.sleep(1)
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
        return f'{imgparts[0]}.mask'

    def __del__(self):
        if not self._has_restored:
            self.restore()

    def mask(self):
        #return self.__default_mask_name() if self._mask == '' else self._mask
        return f'{self._imagename}.mask' if self._mask == '' else self._mask

    def reset(self):
        #if not self._finalized:
        #    raise RuntimeError('attempt to reset a gclean run that has not been finalized')
        self._finalized = False
        self._convergence_result = ( None,
                                     self._convergence_result[1],
                                     self._major_done,
                                     self._nmajor,
                                     self._niter,
                                     self._convergence_result[5] )


    def restore(self):
        """ Restores the final image, and returns a path to the restored image. """
        deconv_ret = self._deconvolve(imagename=self._imagename,
                                      deconvolver=self._deconvolver,
                                      restoration=True, niter=0,
                                      fullsummary=True)

        self._has_restored = True

        return { "image": f"{self._imagename}.image" }

    def has_next(self):
        return not self._finalized
