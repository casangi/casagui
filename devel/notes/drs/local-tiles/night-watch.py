from bokeh.plotting import figure, show
from bokeh.models.renderers import TileRenderer
from bokeh.models.tiles import WMTSTileSource
from bokeh.models.tiles import TMSTileSource
from bokeh.models import WheelZoomTool
from bokeh.models import Range1d
from http.server import test, SimpleHTTPRequestHandler
from os.path import isdir,isfile, join
from os import environ, walk
import subprocess
import tarfile
import certifi
import ssl
import urllib
import sys
import os

## https://upload.wikimedia.org/wikipedia/commons/0/07/Rembrandt_Harmensz._van_Rijn_-_Nachtwacht_-_Google_Art_Project.jpg

if not isdir('night-watch.tms'):
    ###
    ### find gdal2Xtiles.py
    tilegen = None
    for dir in environ['PATH'].split(':'):
        tgs = [ ts for ts in next(walk(dir),(None, None, []))[2] if ts.startswith('gdal2tiles.py') and os.access( join(dir,ts), os.X_OK )  ]
        if len(tgs) > 0:
            tilegen = join( dir, tgs[0] )
            break
    if tilegen:
        print( f'''using {tilegen} to create tiling...''' )
        ###
        ### fetch source image
        ###
        original = 'Rembrandt_Harmensz._van_Rijn_-_Nachtwacht_-_Google_Art_Project.jpg'
        original_url = f'''https://upload.wikimedia.org/wikipedia/commons/0/07/{original}'''
        if not isfile( original ):
            print( f'''fetching {original}...''' )
            try:
                #context = ssl.create_default_context(cafile=certifi.where())
                urllib.request.urlretrieve(original_url, original)
            except urllib.error.URLError:
                print("Failed to open connection to "+original_url)
                raise
        else:
            print( f'''reusing existing {original}...''' )
            ###
            ### generate tiles
            ###
            print( f'''Generating tiling for {original}...''' )
            cmd = [ tilegen, '--tmscompatible', '-p', 'raster', '-z', '0-7', original, 'night-watch.tms' ]
            print( ' '.join(cmd) )
            subprocess.run( cmd )
    else:
        premade_url="https://casa.nrao.edu/download/devel/casavis/data/night-watch.tar.gz"
        print( f'''downloading premade tiles...''' )
        try:
            context = ssl.create_default_context(cafile=certifi.where())
            tstream = urllib.request.urlopen(premade_url, context=context, timeout=400)
            tar = tarfile.open(fileobj=tstream, mode="r:gz")
            tar.extractall( )
        except urllib.error.URLError:
            print("Failed to open connection to "+premade_url)
            raise

p = figure(x_range=(0,28128), y_range=(0,23334))

p=figure( title = 'Night Watch',
          toolbar_location = 'right',  tools = 'pan, wheel_zoom, reset',
          x_axis_type='linear', y_axis_type='linear' )

p.toolbar.active_scroll = p.select_one(WheelZoomTool)


###
### (1) Using 'max_zoom=6' seems to result in it fetching tiles
###     between /0/*/* to /7/*/*
### (2) The 'initial_resolution' is key because it specifies the number of world-pixels per
###     screen pixels at the minimum zoom. This is found in the 'tilemapresource.xml' file
###     that is created by the 'gdal2tiles.py' script. '128' is specific to this particular
###     raster file.
###
tile_source = TMSTileSource( url='http://localhost:8000/night-watch.tms/{z}/{x}/{y}.png',
                             min_zoom=0, max_zoom=6, wrap_around=False,
                             x_origin_offset=0, y_origin_offset=0,
                             initial_resolution=128 )

p.add_tile(tile_source)

###
### set initial zoom
###
p.x_range = Range1d( 13400, 13700 )
p.y_range = Range1d( 11600, 11850 )

show(p)
test(SimpleHTTPRequestHandler)
