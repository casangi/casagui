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

ic = InteractiveClean( vis=ms_path, imagename=img,
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
                       scales=[0,3,10] )

if True:
    print( "Result: %s" % ic( ) )
    print( " Masks: %s" % repr(ic.masks( )) )
else:
    try:
        asyncio.get_event_loop().run_until_complete(ic.show( ))
        asyncio.get_event_loop().run_forever()

    except KeyboardInterrupt:
        print('\nInterrupt received, shutting down ...')
        #os.system('rm -rf {output_image}.* *.html *.log'.format(output_image=output_image))

    print( "Result: %s" % repr(ic.result( )) )
    print( " Masks: %s" % repr(ic.masks( )) )
