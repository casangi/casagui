import os
import numpy as np
import bokeh

from bokeh.layouts import column, row
from bokeh.models import CustomJS, Slider, RadioButtonGroup, TextInput, Button

from components.button.iclean_button import ICleanButton
from components.slider.iclean_slider import ICleanSlider
from components.custom_icon.svg_icon import SVGIcon

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

fig.plot_height = 900
fig.plot_width = 900

# Sliders
slider = ICleanSlider(start=0, end=len(data)-1, value=0, step=1, title="Channel", width=600)

# Button
play_button = ICleanButton(
    label="", 
    button_type="success", 
    width=120, 
    margin=(5,1,5,1), 
    icon=SVGIcon(icon_name="play"))

stop_button = ICleanButton(
    label="", 
    button_type="danger", 
    width=120, 
    margin=(5,1,5,1), 
    icon=SVGIcon(icon_name="stop"))

step_forward_button = ICleanButton(
    label="", 
    button_type="primary", 
    width=120, 
    margin=(5,1,5,1), 
    icon=SVGIcon(icon_name="step-forward"))

step_backward_button = ICleanButton(
    label="", 
    button_type="primary", 
    width=120, 
    margin=(5,1,5,1), 
    icon=SVGIcon(icon_name="step-backward"))

pause_button = ICleanButton(
    label="", 
    button_type="warning", 
    width=120, 
    margin=(5,1,5,1), 
    icon=SVGIcon(icon_name="pause"))

text_input_iter = TextInput(title="Iterations", value="1", width=193)
text_input_cycles = TextInput(title="Cycles", value="1", width=193)
text_input_threshold = TextInput(title="Threshold", value="0.5", width=193)


callback = CustomJS( args=dict( source=source, data=data, slider=slider ),
                                code="""source.data = data[slider.value];""" )

slider.js_on_change('value', callback)
layout = row(
    column(
        row(
            step_backward_button,
            play_button, 
            pause_button, 
            stop_button, 
            step_forward_button),
        row(
            text_input_iter,
            text_input_cycles,
            text_input_threshold),
        slider), 
    fig)

show(layout)
