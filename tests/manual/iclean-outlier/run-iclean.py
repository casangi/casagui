import os
import ssl
import certifi
import urllib
import tarfile

from casagui.apps import iclean

##
## demo measurement set to use
##
ms_path = 'refim_twopoints_twochan.ms'
##
## where to fetch the demo measurement set
##
ms_url = "https://casa.nrao.edu/download/devel/casavis/data/refim_twopoints_twochan-ms.tar.gz"
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

#print("Result = " + str( repr( run_iclean( vis=ms_path, imagename=img,
print("Result = " + str( repr( iclean( vis=ms_path, imagename=img,
                                       imsize=100,
                                       cell='8.0arcsec',
                                       phasecenter="J2000 19:59:28.500 +40.44.01.50",
                                       outlierfile='test_outlier.txt',
                                       niter=50,
                                       cycleniter=10,
                                       deconvolver='hogbom',
                                       specmode='mfs',
                                       spw='0:0') ) ) )
