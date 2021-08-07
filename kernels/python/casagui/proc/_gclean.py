import os
import asyncio
import functools

def _tclean( *args, **kwargs ):
    from casatasks import tclean
    arg_s = ', '.join(args)
    kw_s = ', '.join( map( lambda kv: "%s=%s" % (kv[0],kv[1]), kwargs.items()) )
    if len(arg_s) > 0 and len(ks_s) > 0:
        parameters = arg_s + ", " + kw_s
    else:
        parameters = arg_s + kw_s
    print( "tclean( %s )" % parameters  )
    return tclean( *args, **kwargs )

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

    def __init__( self, vis, imagename, imsize=[100], cell="1arcsec", specmode='cube', nchan=-1, start='',
                  width='', interpolation='linear', gridder='standard', pblimit=0.2, deconvolver='hogbom',
                  niter=0, cyclefactor=1.0, scales=[] ):
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
        self._cyclefactor = cyclefactor
        self._scales = scales
        self._howmany = 4 # <<<---------<<<<<< arbitray arbitrary limit for debugging
        if len(list(filter(lambda f: os.path.isdir(f) and f.startswith(self._imagename + '.'), os.listdir( os.curdir )))) > 0:
            raise RuntimeError("image files already exist")
        self._convergence_rec = None        

    def __next__( self ):
        if self._howmany <= 0:
            raise StopIteration
        self._howmany -= 1
        if self._niter < 1:
            print("warning, nothing to run, niter == %s" % self._niter)
            return self._convergence_rec
        else:
            if self._convergence_rec is None:
                # initial call to tclean(...) creates the initial dirty image with niter=0
                self._convergence_rec = _tclean( vis=self._vis, imagename=self._imagename, imsize=self._imsize, cell=self._cell,
                                                 specmode=self._specmode, interpolation=self._interpolation, nchan=self._nchan,
                                                 start=self._start, width=self._width, pblimit=self._pblimit, deconvolver=self._deconvolver,
                                                 niter=0, cyclefactor=self._cyclefactor, scales=self._scales, interactive=0 )
                self._convergence_rec['cleanstate'] = 'dirty'
            else:

                self._convergence_rec = _tclean( vis=self._vis, imagename=self._imagename, imsize=self._imsize, cell=self._cell,
                                                 specmode=self._specmode, interpolation=self._interpolation, nchan=self._nchan,
                                                 start=self._start, width=self._width, pblimit=self._pblimit, deconvolver=self._deconvolver,
                                                 niter=self._niter, cyclefactor=self._cyclefactor, scales=self._scales, interactive=0,
                                                 restart=True, calcpsf=False, calcres=False,
                                                 cycleniter=self._niter, threshold=0, maxpsffraction=1, minpsffraction=0
                                                 #, cyclefactor=0.01
                                                )
            img = '%s.image' % self._imagename
            if os.path.exists( img ):
                self._convergence_rec['image'] = os.path.abspath(img)
            else:
                self._convergence_rec['image'] = None

            return self._convergence_rec

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

