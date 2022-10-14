import numpy as np
from bokeh.plotting import figure, show, ColumnDataSource
from casatools import image

from bokeh.models import Button, CustomJS
from bokeh.layouts import row, column

import os, ssl, urllib, certifi, tarfile

image_path = 'GCcube.image'
mask_path = 'GCcube.mask'

data_url = "https://casa.nrao.edu/download/devel/casavis/data/GCcube.tar.gz"

if not os.path.isdir(image_path) or not os.path.isdir(mask_path):
    try:
        context = ssl.create_default_context(cafile=certifi.where())
        tstream = urllib.request.urlopen(data_url, context=context, timeout=400)
        tar = tarfile.open(fileobj=tstream, mode="r:gz")
        tar.extractall( )
    except urllib.error.URLError:
        print("Failed to open connection to "+data_url)
        raise

if not os.path.isdir(image_path) or not os.path.isdir(mask_path):
    raise  RuntimeError("Failed to fetch image or mask")

mask = image( )
im = image( )

im.open(image_path)
mask.open(mask_path)
shape = list(im.shape())

###
### Channel #58
###
chan_m = np.squeeze(mask.getchunk( [0,0,0,58], shape[:2] + [0,58] )).astype(np.bool_).transpose( )
chan_i = np.squeeze(im.getchunk( [0,0,0,58], shape[:2] + [0,58] )).transpose( )

s = ColumnDataSource( data=dict( img=[ chan_i ], msk=[ chan_m ] ) ) 
p = figure( )
i = p.image( image='img', x=0, y=0, dw=shape[0], dh=shape[1], source=s, palette= 'Spectral11' )
m = p.image( image='msk', x=0, y=0, dw=shape[0], dh=shape[1], source=s, palette=['rgba(0, 0, 0, 0)','blue'] )
b = Button( label='debug' )

contour = '''function contour( ary ) {
                 console.group('image')
                 console.log(ary.data.img)
                 console.log(ary.data.img[0][0])
                 console.log(ary.data.img[0][9999])
                 console.groupEnd( )
                 console.group('mask')
                 console.log(ary.data.msk)
                 console.groupEnd( )
                 console.log('>>>', ary)
             }'''
b.js_on_click( CustomJS( args=dict(image=i,mask=m,source=s),
                         code=contour +
                              '''console.group('image')
                                 console.log(image)
                                 contour(source)
                                 console.groupEnd( )
                                 console.group('mask')
                                 console.log(mask)
                                 console.groupEnd( )
                                 mask.visible = ! mask.visible''' ) )

c = column( p, b );
show(c)
