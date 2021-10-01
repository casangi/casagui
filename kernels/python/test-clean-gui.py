import os
import asyncio
import urllib
import tarfile
#from casagui.bokeh.state import initialize_bokeh
#initialize_bokeh( "casaguijs/dist/casaguijs.min.js" )        ### local build

from casagui.proc.imaging import iclean

##
## demo measurement set to use
##
ms_path = 'refim_point_withline.ms'
##
## were to fetch the demo measurement set
##
ms_url = "https://casa.nrao.edu/download/devel/casavis/data/refim_point_withline-ms.tar.gz"
##
## output image file name
##
img = 'test'

if not os.path.isdir(ms_path):
    tstream = urllib.request.urlopen(ms_url)
    tar = tarfile.open(fileobj=tstream, mode="r:gz")
    tar.extractall()


ic = iclean( vis=ms_path, imagename=img,
             imsize=512, 
             cell='12.0arcsec', 
             specmode='cube', 
             interpolation='nearest', 
             nchan=5, 
             start='1.0GHz', 
             width='0.2GHz', 
             pblimit=-1e-05, 
             deconvolver='hogbom', 
             niter=500, 
             cyclefactor=3, 
             scales=[0,3,10] )

if True:
    ic.show( )
else:
    try:
        asyncio.get_event_loop().run_until_complete(ic.show(False))
        asyncio.get_event_loop().run_forever()

    except KeyboardInterrupt:
        print('\nInterrupt received, shutting down ...')
        #os.system('rm -rf {output_image}.* *.html *.log'.format(output_image=output_image))
