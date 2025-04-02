import os
import ssl
import certifi
import urllib
import tarfile

from os.path import splitext
from os.path import split as splitpath
from casagui.apps import iclean

from argparse import ArgumentParser
name = splitext(splitpath(__file__)[1])[0]

argparse = ArgumentParser( prog=name, description='Basic tests of iclean' )
argparse.add_argument( '--twopoint', action='store_true',
                       help='use refim_twopoints_twochan.ms instead of refim_point_withline.ms' )
args = argparse.parse_args( )

if args.twopoint:
    img = 'test2pt'
    ms_path = 'refim_twopoints_twochan.ms'
    ms_url = "https://casa.nrao.edu/download/devel/casavis/data/refim_twopoints_twochan-ms.tar.gz"
    cleanargs = dict( cell='8.0arcsec', phasecenter="J2000 19:59:28.500 +40.44.01.50",
                      deconvolver='hogbom', specmode='cube' )
else:
    img = 'test'
    ms_path = 'refim_point_withline.ms'
    ms_url = "https://casa.nrao.edu/download/devel/casavis/data/refim_point_withline-ms.tar.gz"
    cleanargs = dict( cell='12.0arcsec', specmode='cube', interpolation='nearest',
                      nchan=5, start='1.0GHz', width='0.2GHz', pblimit=-1e-05,
                      deconvolver='hogbom', threshold='0.001Jy', cyclefactor=3, scales=[0,3,10] )

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

print("Result = " + str( repr( iclean( vis=ms_path, imagename=img,
                                       imsize=512, niter=50,
                                       cycleniter=10,
                                       **cleanargs ) ) ) )
