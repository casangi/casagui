import os
import ssl
import certifi
import asyncio
import urllib
import tarfile
#from casagui.bokeh.state import initialize_bokeh
#initialize_bokeh( bokeh='../../../casaguijs/dist/casaguijs.js' )                  ### local gui/js build + standard bokeh independent library
from casagui.apps import createregion

##
## demo measurement set to use
##
image_paths = [ 'ngc6503.clean.image', 'IRC10216_HC3N.cube_r0.5.image' ]
##
## where to fetch the demo measurement set
##
image_urls = [ 'https://casa.nrao.edu/download/devel/casavis/data/ngc6503.clean.image.tar.gz',
               'https://casa.nrao.edu/download/devel/casavis/data/IRC10216_HC3N.cube_r0.5.image.tar.gz' ]

for paths in zip( image_paths, image_urls ):
    if not os.path.isdir(paths[0]):
        try:
            context = ssl.create_default_context(cafile=certifi.where())
            tstream = urllib.request.urlopen(paths[1], context=context, timeout=400)
            tar = tarfile.open(fileobj=tstream, mode="r:gz")
            tar.extractall()
        except urllib.error.URLError:
            print("Failed to open connection to "+paths[1])
            raise

result = createregion( image_paths )
print(result)

for img, regions in result.items( ):
    print(img)
    for region_tuple in regions:
        print( f'''\t{region_tuple}''' )
        ### Python is lame:   >>>>>--------+                  replace(   '\n', '\n\t'        )
        ### --------------                 |
        ###                                +------------------VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV
        #print( f'''\t{str(region_tuple[1].to_astropy_sky( )).replace(chr(10), chr(10)+chr(9))}''' )
        print( '\t' + str(region_tuple[1].to_astropy_sky( )).replace('\n', '\n\t') )
