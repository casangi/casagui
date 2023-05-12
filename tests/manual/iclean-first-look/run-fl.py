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
ms_path = 'twhya_smoothed.ms'
##
## where to fetch the demo measurement set
##
ms_url = "https://casa.nrao.edu/download/devel/casavis/data/twhya_smoothed.tar.gz"
##
## output image file name
##
img = 'twhya_cont'

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
                       field='0',
                       spw='',
                       specmode='mfs',
                       gridder='standard',
                       deconvolver='hogbom',
                       imsize=[250,250],
                       cell=['0.08arcsec'],
                       weighting='briggs',
                       robust=0.5,
                       threshold='0mJy',
                       niter=5000 )

try:
    res = ic()
    print("Result = " + str(repr(res)))

except KeyboardInterrupt:
    print('\nInterrupt received, shutting down ...')
    # os.system('rm -rf {img}.* *.html *.log'.format(img=img))

print("End of Interactive Clean")
