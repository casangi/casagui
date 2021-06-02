import os
import numpy as np
from bokeh.layouts import column, row
from bokeh.models import CustomJS, Slider, RadioButtonGroup, TextInput
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
fig = figure(tooltips=[("x", "$x"), ("y", "$y"), ("value", "@image")], output_backend="webgl")
fig.x_range.range_padding = fig.y_range.range_padding = 0
fig.image(image="d", x=0, y=0, dw=cube.shape[0], dh=cube.shape[1], palette="Spectral11", level="image", source=source )
fig.grid.grid_line_width = 0.5

# Sliders
slider = Slider(start=0, end=len(data)-1, value=0, step=1, title="Channel")

# Button Group
LABELS=['Stop', 'Play', 'Step']

radio_button_group = RadioButtonGroup(labels=LABELS, active=0)
radio_button_group.js_on_click(CustomJS(code="""
    console.log('radio_button_group: active=' + this.active, this.toString())
"""))

# Text Input

text_input_iter = TextInput(title="Iterations", value="1")
text_input_cycles = TextInput(title="Cycles", value="1")
text_input_threshold = TextInput(title="Threshold", value="0.5")


callback = CustomJS( args=dict( source=source, data=data, slider=slider ),
                                code="""source.data = data[slider.value];""" )

slider.js_on_change('value', callback)
layout = column( fig,
                 radio_button_group,
                 row(
                     text_input_iter,
                     text_input_cycles,
                     text_input_threshold),
                 slider )
show(layout)
