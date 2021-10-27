import os
import asyncio
from functools import reduce

class gclean:
    '''gclean(...) creates a stream of convergence records which indicate
    the convergence quaility of the tclean process. The initial record
    describes the initial dirty image.

    It is designed for use with the interactive clean GUI, but it could
    be used independently. It can be used as a regular generator:

          for rec in gclean( vis='refim_point_withline.ms', imagename='test', imsize=512, cell='12.0arcsec',
                             specmode='cube', interpolation='nearest', nchan=5, start='1.0GHz', width='0.2GHz',
                             pblimit=-1e-05, deconvolver='hogbom', niter=500, cyclefactor=3, scales=[0, 3, 10] ):
              # use rec to decide when to stop
              print(rec)

    or as an async generator:

          async for rec in gclean( vis='refim_point_withline.ms', imagename='test', imsize=512, cell='12.0arcsec',
                                   specmode='cube', interpolation='nearest', nchan=5, start='1.0GHz', width='0.2GHz',
                                   pblimit=-1e-05, deconvolver='hogbom', niter=500, cyclefactor=3, scales=[0, 3, 10] ):
              # use rec to decide when to stop
              print(rec)
    '''

    def _tclean( self, *args, **kwargs ):
        from casatasks import tclean
        arg_s = ', '.join(map( lambda a: repr(a), args ))
        kw_s = ', '.join( map( lambda kv: "%s=%s" % (kv[0],repr(kv[1])), kwargs.items()) )
        if len(arg_s) > 0 and len(ks_s) > 0:
            parameters = arg_s + ", " + kw_s
        else:
            parameters = arg_s + kw_s
        self._exe_cmds.append( "tclean( %s )" % parameters )
        return tclean( *args, **kwargs )

    def cmds( self ):
        return self._exe_cmds

    def update( self, msg ):
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
        if 'mask' in msg:
            self._mask = msg['mask']

    def __init__( self, vis, imagename, imsize=[100], cell="1arcsec", specmode='cube', nchan=-1, start='',
                  width='', interpolation='linear', gridder='standard', pblimit=0.2, deconvolver='hogbom',
                  niter=0, threshold='0.1Jy', cycleniter=-1, cyclefactor=1.0, scales=[] ):
        self._vis = vis
        self._imagename = imagename
        self._imsize = imsize
        self._cell = cell
        self._specmode = specmode
        self._nchan = nchan
        self._start = start
        self._width = width
        self._interpolation = interpolation
        self._gridder = gridder
        self._pblimit = pblimit
        self._deconvolver = deconvolver
        self._niter = niter
        self._threshold = threshold
        self._cycleniter = cycleniter
        self._cyclefactor = cyclefactor
        self._mask = ''
        self._scales = scales
        self._exe_cmds = [ ]

        if len(list(filter(lambda f: os.path.isdir(f) and f.startswith(self._imagename + '.'), os.listdir( os.curdir )))) > 0:
            raise RuntimeError("image files already exist")
        self._convergence_result = (None,None)

    def __filter_convergence( raw ):
        ###
        ### this function filters out the pieces of the `raw` tclean return dictionary
        ### that we care about
        ###
        ### the first index in the `raw` dictionary is the channel axis
        ### each channel may have a number of polarity dictionaries
        ###
        return  { channel_k: {
                      stokes_k: { mapping: stokes_v[mapping] for mapping in
                                      [ 'modelFlux', 'iterDone', 'peakRes' ]
                                }
                      for stokes_k,stokes_v in channel_v.items( ) } for channel_k,channel_v in raw.items( )
                }

    def __update_convergence( oldconv, newconv ):
        def update_one( prevdone, old, new ):
            if 'iterDone' in new:
                new['iterations'] = reduce( lambda acc, v: (acc[0]+v, acc[1] + [v + prevdone + acc[0]]), new['iterDone'], (0,[]) )[1]
                ### we converted to from a vector of iteration counts to a normal sequence
                ### so the key changes from 'iterDone' to 'iterations'
                del new['iterDone']
            return { key: old[key] + new[key] for key in new.keys( ) }
        if oldconv is None:
            ### substitute 'iterations' for 'iterDone'
            return { chan_k: {
                       stokes_k: {
                         k: v for k,v in
                           map( lambda x: ('iterations' if x[0] == 'iterDone' else x[0], x[1]),
                                stokes_v.items( ) )
                       } for stokes_k,stokes_v in chan_v.items()
                     } for chan_k,chan_v in newconv.items() }
        else:
            return { channel_k: {
                         stokes_k: update_one( max(oldconv[channel_k][stokes_k]['iterations']) if 'iterations' in oldconv[channel_k][stokes_k] else 0,
                                               oldconv[channel_k][stokes_k], stokes_v )
                         for stokes_k,stokes_v in channel_v.items( ) } for channel_k,channel_v in newconv.items( )
                   }

    def __next__( self ):
        if self._niter < 1:
            print("warning, nothing to run, niter == %s" % self._niter)
            return self._convergence_result
        else:
            if self._convergence_result[0] is None:
                # initial call to tclean(...) creates the initial dirty image with niter=0
                tclean_ret = self._tclean( vis=self._vis, imagename=self._imagename, imsize=self._imsize, cell=self._cell,
                                           specmode=self._specmode, interpolation=self._interpolation, nchan=self._nchan,
                                           start=self._start, width=self._width, pblimit=self._pblimit, deconvolver=self._deconvolver,
                                           niter=1, cyclefactor=self._cyclefactor, scales=self._scales, interactive=0, gain=0.000001 )
            else:
                tclean_ret = self._tclean( vis=self._vis, imagename=self._imagename, imsize=self._imsize, cell=self._cell,

                                           specmode=self._specmode, interpolation=self._interpolation, nchan=self._nchan,
                                           start=self._start, width=self._width, pblimit=self._pblimit, deconvolver=self._deconvolver,
                                           niter=self._niter, cyclefactor=self._cyclefactor, scales=self._scales, interactive=0,
                                           restart=True, calcpsf=False, calcres=False,
                                           threshold=self._threshold, cycleniter=self._cycleniter,
                                           maxpsffraction=1, minpsffraction=0, mask=self._mask )

            new_rec = gclean.__filter_convergence(tclean_ret['summaryminor'])
            self._convergence_result = ( tclean_ret['stopcode'] if 'stopcode' in tclean_ret else 0,
                                         gclean.__update_convergence(self._convergence_result[1],new_rec) )
            return self._convergence_result

    def __reflect_stop( self ):
        ## if python wasn't hacky, you would be able to try/except/raise in lambda
        try:
            return self.__next__( )
        except StopIteration:
            raise StopAsyncIteration

    async def __anext__( self ):
        loop = asyncio.get_event_loop( )
        return await loop.run_in_executor( None, self.__reflect_stop )

    def __iter__( self ):
        return self

    def __aiter__( self ):
        return self
