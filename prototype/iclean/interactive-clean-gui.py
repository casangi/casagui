import os
import numpy as np
from bokeh.layouts import column
from bokeh.models import CustomJS, Slider
from bokeh.plotting import ColumnDataSource, figure, show
from casatools import image

import urllib.request
import tarfile

img = 'g35.03_II_nh3_11.hline.image'
url = "https://casa.nrao.edu/download/devel/casavis/data/g35-hline-img.tar.gz"

if not os.path.isdir(img):
    tstream = urllib.request.urlopen(url)
    tar = tarfile.open(fileobj=tstream, mode="r:gz")
    tar.extractall()

_ia = image( )
_ia.open(img)

cube = _ia.getchunk( )

data = [ ]
for i in range(40, 45):
    data.append({'d': [ cube[:,:,0,i].transpose()]})

_ia.close( )

source = ColumnDataSource( data=data[0] )
fig = figure(tooltips=[("x", "$x"), ("y", "$y"), ("value", "@image")])
fig.x_range.range_padding = fig.y_range.range_padding = 0
fig.image(image="d", x=0, y=0, dw=cube.shape[0], dh=cube.shape[1], palette="Spectral11", level="image", source=source )
fig.grid.grid_line_width = 0.5

slider = Slider(start=0, end=len(data)-1, value=0, step=1, title="Channel")

callback = CustomJS( args=dict( source=source, data=data, slider=slider ),
                                code="""
    source.data = data[slider.value];
""" )
slider.js_on_change('value', callback)
layout = column( fig, slider )
show(layout)
