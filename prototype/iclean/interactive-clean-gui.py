import os
import numpy as np
import bokeh

from bokeh.layouts import column, row
from bokeh.models import CustomJS, Slider, RadioButtonGroup, TextInput, Button, BoxAnnotation, PreText
from bokeh.events import SelectionGeometry
from bokeh.plotting import ColumnDataSource, figure, show

from components.button.iclean_button import ICleanButton
from components.slider.iclean_slider import ICleanSlider
from components.custom_icon.svg_icon import SVGIcon

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
fig = figure(
    tooltips=[("x", "$x"), ("y", "$y"), ("value", "@image")], 
    output_backend="webgl", 
    tools=["box_select", "pan,wheel_zoom","box_zoom","save", "reset", "help"])

fig.x_range.range_padding = fig.y_range.range_padding = 0
fig.image(image="d", x=0, y=0, dw=cube.shape[0], dh=cube.shape[1], palette="Spectral11", level="image", source=source )
fig.grid.grid_line_width = 0.5

fig.plot_height = 900
fig.plot_width = 900

box = BoxAnnotation(left=0, right=0, bottom=0, top=0,
    fill_alpha=0.1, line_color='black', fill_color='black')

jscode = """
    box[%r] = cb_obj.start
    box[%r] = cb_obj.end
"""


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

mask = PreText(text='', width=600)

fig.js_on_event(
    SelectionGeometry, 
    CustomJS(args=dict(source=source, box=box, mask=mask), code="""
    const geometry = cb_obj['geometry']
    const data = source.data
    console.log(geometry)
    
    box['left'] = geometry['x0']
    box['right'] = geometry['x1']
    box['top'] = geometry['y0']
    box['bottom'] = geometry['y1']   

    mask.text = "Mask Coordinates: " + geometry['type'] 
    + "\\n\\nX: " + geometry['x0'] + " " + geometry['x1'] 
    + "\\nY: " + geometry['y0'] + " " + geometry['y1']

    source.change.emit()
"""))

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
        slider, mask), 
    fig)

fig.add_layout(box)
show(layout)
