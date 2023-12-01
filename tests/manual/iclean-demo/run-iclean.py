import os
import ssl
import certifi
import urllib
import tarfile

from casagui.apps import run_iclean

##
## demo measurement set to use
##
ms_path = 'refim_point_withline.ms'
##
## where to fetch the demo measurement set
##
ms_url = "https://casa.nrao.edu/download/devel/casavis/data/refim_point_withline-ms.tar.gz"
##
## output image file name
##
img = 'test'

if not os.path.isdir(ms_path):
    try:
        context = ssl.create_default_context(cafile=certifi.where())
        tstream = urllib.request.urlopen(ms_url, context=context, timeout=400)
        tar = tarfile.open(fileobj=tstream, mode="r:gz")
        tar.extractall( )
    except urllib.error.URLError:
        print("Failed to open connection to "+ms_url)
        raise

if not os.path.isdir(ms_path):
    raise  RuntimeError("Failed to fetch measurement set")

print("Result = " + str( repr( run_iclean( vis=ms_path, imagename=img,
                                           imsize=512,
                                           cell='12.0arcsec',
                                           specmode='cube',
                                           interpolation='nearest',
                                           nchan=5,
                                           start='1.0GHz',
                                           width='0.2GHz',
                                           pblimit=-1e-05,
                                           deconvolver='hogbom',
                                           threshold='0.001Jy',
                                           niter=50,
                                           cycleniter=10,
                                           cyclefactor=3,
                                           scales=[0,3,10] ) ) ) )
