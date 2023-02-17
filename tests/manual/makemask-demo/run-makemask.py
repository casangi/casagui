import os
import ssl
import certifi
import asyncio
import urllib
import tarfile
#from casagui.bokeh.state import initialize_bokeh
#initialize_bokeh( bokeh='../../../casaguijs/dist/casaguijs.js' )                  ### local gui/js build + standard bokeh independent library
from casagui.apps import MakeMask

##
## demo measurement set to use
##
image_path = 'refim_point_withline.image'
##
## where to fetch the demo measurement set
##
image_url = "https://casa.nrao.edu/download/devel/casavis/data/refim_point_withline-image.tar.gz"

if not os.path.isdir(image_path):
    try:
        context = ssl.create_default_context(cafile=certifi.where())
        tstream = urllib.request.urlopen(image_url, context=context, timeout=400)
        tar = tarfile.open(fileobj=tstream, mode="r:gz")
        tar.extractall()
    except urllib.error.URLError:
        print("Failed to open connection to "+image_url)
        raise

print(repr(MakeMask( image_path )( )))
