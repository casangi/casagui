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

from casagui.apps import InteractiveClean

##
## demo measurement set to use
##
ms_path = 'sis14_twhya_selfcal.ms'
##
## where to fetch the demo measurement set
##
ms_url = "https://casa.nrao.edu/download/devel/casavis/data/sis14_twhya_selfcal.ms.tar.gz"
##
## output image file name
##
img = 'twhya_n2hp'

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

ic = InteractiveClean( vis=ms_path, imagename=img,
                       field = '0',
                       spw = '0',
                       specmode = 'cube',
                       nchan = 15,
                       start = '0.0km/s',
                       width = '0.5km/s',
                       outframe = 'LSRK',
                       restfreq = '372.67249GHz',
                       deconvolver= 'hogbom',
                       gridder = 'standard',
                       imsize = 1024,
                       cell = '0.08arcsec',
                       phasecenter = 0,
                       weighting = 'briggs',
                       robust = 0.5,
                       restoringbeam='common',
                       niter=5000 )

try:
    res = ic()
    print("Result = " + str(repr(res)))

except KeyboardInterrupt:
    print('\nInterrupt received, shutting down ...')
    # os.system('rm -rf {img}.* *.html *.log'.format(img=img))

print("End of Interactive Clean")
