import os
import ssl
import certifi
import asyncio
import urllib
import tarfile

import datetime
import numpy as np
from time import process_time
from casatools import image
from casatasks import tclean

ms_path = 'refim_point_withline.ms'
ms_url = "https://casa.nrao.edu/download/devel/casavis/data/refim_point_withline-ms.tar.gz"

if not os.path.isdir(ms_path):
    try:
        context = ssl.create_default_context(cafile=certifi.where())
        tstream = urllib.request.urlopen(ms_url, context=context, timeout=400)
        tar = tarfile.open(fileobj=tstream, mode="r:gz")
        tar.extractall( )
    except urllib.error.URLError:
        print("Failed to open connection to "+ms_url)
        raise

t = process_time()
tclean( vis='refim_point_withline.ms', mask='', imagename='dirty', imsize=4096, cell='12.0arcsec', phasecenter='', stokes='I', startmodel='', specmode='cube', reffreq='', gridder='standard', wprojplanes=1, mosweight=True, psterm=False, wbawp=True, conjbeams=False, usepointing=False, interpolation='nearest', perchanweightdensity=True, nchan=5, start='1.0GHz', width='0.2GHz', outframe='LSRK', pointingoffsetsigdev=[], pblimit=-1e-05, deconvolver='hogbom', cyclefactor=3, scales=[0, 3, 10], restoringbeam='', pbcor=False, nterms=2, field='', spw='', timerange='', uvrange='', antenna='', scan='', observation='', intent='', datacolumn='corrected', weighting='natural', robust=0.5, npixels=0, interactive=False, niter=1, gain=1e-06, calcres=True, restoration=False, parallel=False )
elapsed_time = process_time() - t

print('elapsed time')
print('--------------------------------------------------------------------------------')
print(f'''initial dirty image: {str(datetime.timedelta(seconds=elapsed_time))}''')

t = process_time()
tclean( vis='refim_point_withline.ms', imagename='dirty', imsize=4096, cell='12.0arcsec', phasecenter='', stokes='I', specmode='cube', reffreq='', gridder='standard', wprojplanes=1, mosweight=True, psterm=False, wbawp=True, conjbeams=False, usepointing=False, interpolation='nearest', perchanweightdensity=True, nchan=5, start='1.0GHz', width='0.2GHz', outframe='LSRK', pointingoffsetsigdev=[], pblimit=-1e-05, deconvolver='hogbom', cyclefactor=3, scales=[0, 3, 10], restoringbeam='', pbcor=False, nterms=2, field='', spw='', timerange='', uvrange='', antenna='', scan='', observation='', intent='', datacolumn='corrected', weighting='natural', robust=0.5, npixels=0, interactive=False, niter=50, restart=True, calcpsf=False, calcres=False, restoration=False, threshold='0.001Jy', nsigma=0.0, cycleniter=10, nmajor=1, gain=0.1, sidelobethreshold=3.0, noisethreshold=5.0, lownoisethreshold=1.5, negativethreshold=0.0, minbeamfrac=0.3, growiterations=75, dogrowprune=True, minpercentchange=-1.0, fastnoise=True, savemodel='none', maxpsffraction=1, minpsffraction=0, parallel=False )
elapsed_time = process_time() - t

print(f'''    one major cycle: {str(datetime.timedelta(seconds=elapsed_time))}''')
ia = image( )
ia.open('dirty.residual')
shape = ia.shape( )
t = process_time()
chan = np.squeeze(ia.getchunk( blc=[0,0,0,0], trc=list(shape[0:2])+[0,0] )).transpose( )
elapsed_time = process_time() - t
print(f'''           getchunk: {str(datetime.timedelta(seconds=elapsed_time))}''')
