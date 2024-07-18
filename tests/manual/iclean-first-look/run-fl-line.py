#from casagui.bokeh.state import initialize_bokeh
#initialize_bokeh( "../../../casalib/dist/esbuild/casalib-v0.0.1.min.js",
#                  "../../../casaguijs/dist/casaguijs.js" )                        ### local build
#initialize_bokeh( "../../../casalib/dist/esbuild/casalib-v0.0.2.min.js" )
#
#initialize_bokeh( bokeh='../../../casaguijs/dist/casaguijs.js' )                  ### local gui/js build + standard bokeh independent library

import os
import ssl
import certifi
import asyncio
import urllib
import tarfile

from casagui.apps import iclean

##
## demo measurement set to use
##
ms_path = 'twhya_selfcal_contsub.ms'
##
## where to fetch the demo measurement set
##
ms_url = "https://casa.nrao.edu/download/devel/casavis/data/twhya_selfcal_contsub_ms.tar.gz"
##
## output image file name
##
img =  'twhya_n2hp'

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
                                       field = '5',
                                       spw = '0',
                                       specmode = 'cube',
                                       perchanweightdensity=True,
                                       nchan = 15,
                                       start = '0.0km/s',
                                       width = '0.5km/s',
                                       outframe = 'LSRK',
                                       restfreq = '372.67249GHz',    ### N2H+ rest frequency
                                       deconvolver= 'hogbom',
                                       gridder = 'standard',
                                       imsize = [500, 500],
                                       cell = '0.1arcsec',
                                       weighting = 'briggsbwtaper',
                                       robust = 0.5,
                                       restoringbeam='common',
                                       niter=100 ) ) ) )
