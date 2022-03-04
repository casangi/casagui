import os
import asyncio
import urllib
import tarfile
#from casagui.bokeh.state import initialize_bokeh
#initialize_bokeh( ".../casagui/casaguijs/dist/casaguijs.min.js" )        ### local build

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
    tstream = urllib.request.urlopen(image_url)
    tar = tarfile.open(fileobj=tstream, mode="r:gz")
    tar.extractall()

print(repr(MakeMask( image_path )( )))
