import os
import numpy as np
import bokeh

from bokeh.layouts import column, row
from bokeh.models import CustomJS, Slider, RadioButtonGroup, TextInput, Button, BoxAnnotation, PreText, Range1d, LinearAxis, Span, HoverTool
from bokeh.events import SelectionGeometry
from bokeh.plotting import ColumnDataSource, figure, show

from casagui.bokeh.state import initialize_bokeh
#initialize_bokeh( "casaguijs/dist/casaguijs.min.js" )        ### local build
initialize_bokeh( )                                           ### fetch from https://casa.nrao.edu/
from casagui.bokeh.sources import ImageDataSource, SpectraDataSource, ImagePipe
from casagui.bokeh.components.button.iclean_button import ICleanButton
from casagui.bokeh.components.slider.iclean_slider import ICleanSlider
from casagui.bokeh.components.custom_icon.svg_icon import SVGIcon

from casatools import image
from casatasks import tclean

from casagui.utils import find_ws_address

import urllib.request
import tarfile
import asyncio
import websockets

def __build_data(data):
"""
    This function takes in the data array that defines containing the residual and total flu information
    and builds a convenient dictionary array.

    Example:
        The ``data`` array comes as a retuen value of the tclean process::

            $ data = tclean( .... )
            $ __build_data(data)

    Attributes:
        data (numpy.ndarray): Contains data for iteration, residual, total flux, channel.

    Todo:
        * Add support for other array indexs that aren't currenlty used as well as polarization.
        * You have to also use ``sphinx.ext.todo`` extension
"""

  chan = data[5,:]
  iteration = data[0,:]
  residual = data[1,:]
  flux = data[2,:]

  data_dict = []
  for i in range(int(chan.max())):
    data_dict.append({
      'iteration':iteration[chan==i],
      'residual':residual[chan==i],
      'flux':flux[chan==i]
  }) 
  
  return data_dict

img = 'g35.03_II_nh3_11.hline.image'

rec = tclean(
    vis='refim_point_withline.ms', 
    imagename='test', 
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
    scales=[0,3,10], 
    interactive=0)


pipe = ImagePipe( image=img, address=find_ws_address( ) )
source = ImageDataSource( image_source=pipe )
spectra = SpectraDataSource( image_source=pipe )
shape = pipe.shape()

pos_cb = CustomJS( args=dict(spectra=spectra),
                   code = """var geometry = cb_data['geometry'];
                             var x_pos = Math.floor(geometry.x);
                             var y_pos = Math.floor(geometry.y);
                             spectra.spectra(x_pos,y_pos)
                          """ )

hover_tool = HoverTool(callback=pos_cb)

spectral_figure = figure(
    plot_height=150, 
    plot_width=650, 
    title=None, 
    tools=[ ])

spectral_figure.x_range.range_padding = spectral_figure.y_range.range_padding = 0
spectral_figure.line(
    x='x', 
    y='y', 
    source=spectra)

spectral_figure.grid.grid_line_width = 0.5

major = rec['summarymajor']
minor = rec['summaryminor']

minor_converge_dict = __build_data(minor)

converge_source = ColumnDataSource(data=minor_converge_dict[0])

converge_data_major = [{'iteration': major}]

converge_figure = figure(
    tooltips=[("x", "$x"), ("y", "$y"), ("value", "@image")], 
    output_backend="webgl", 
    tools=["box_select", "pan,wheel_zoom","box_zoom","save", "reset", "help"],
    title='Convergance', x_axis_label='Iteration', y_axis_label='Peak Residual')

converge_figure.extra_y_ranges = {
    'flux': Range1d(
        converge_source.data['flux'].min()*0.5,
        converge_source.data['flux'].max()*2
    )
}
converge_figure.add_layout(LinearAxis(y_range_name='flux', axis_label='Total Flux'), 'right')

for i in major:
    major_cycle = Span(
        location=i, 
        dimension='height', 
        line_color='slategray', 
        line_dash='dashed', 
        line_width=2)

    converge_figure.add_layout(major_cycle)

converge_figure.circle(
    x='iteration', 
    y='residual', 
    color='crimson', 
    size=10, 
    alpha=0.4, 
    legend_label='Peak Residual',
    source=converge_source)

converge_figure.circle(
    x='iteration', 
    y='flux', 
    color='forestgreen', 
    size=10, 
    alpha=0.4, 
    y_range_name='flux', 
    legend_label='Total Flux',
    source=converge_source)

converge_figure.line(
    x='iteration', 
    y='residual', 
    color='crimson',
    source=converge_source)

converge_figure.line(
    x='iteration', 
    y='flux', 
    color='forestgreen', 
    y_range_name='flux',
    source=converge_source)

converge_figure.plot_height = 650
converge_figure.plot_width = 650


image_figure = figure(
    tooltips=[("x", "$x"), ("y", "$y"), ("value", "@d")], 
    output_backend="webgl", 
    tools=["box_select", "pan,wheel_zoom","box_zoom", hover_tool, "save", "reset", "help"])

image_figure.x_range.range_padding = image_figure.y_range.range_padding = 0
image_figure.image(
    image="d", 
    x=0, 
    y=0, 
    dw=shape[0], 
    dh=shape[1], 
    palette="Spectral11", 
    level="image", source=source )

image_figure.grid.grid_line_width = 0.5

image_figure.plot_height = 800
image_figure.plot_width = 800

box = BoxAnnotation(
    left=0, 
    right=0, 
    bottom=0, 
    top=0,
    fill_alpha=0.1, 
    line_color='black', 
    fill_color='black')

jscode = """
    box[%r] = cb_obj.start
    box[%r] = cb_obj.end
"""

# Button
play_button = ICleanButton(
    label="", 
    button_type="success", 
    width=75, 
    margin=(5,1,5,1), 
    icon=SVGIcon(icon_name="play"))

stop_button = ICleanButton(
    label="", 
    button_type="danger", 
    width=75, 
    margin=(5,1,5,1), 
    icon=SVGIcon(icon_name="stop"))

step_forward_button = ICleanButton(
    label="", 
    button_type="primary", 
    width=75, 
    margin=(5,1,5,1), 
    icon=SVGIcon(icon_name="step-forward"))

step_backward_button = ICleanButton(
    label="", 
    button_type="primary", 
    width=75, 
    margin=(5,1,5,1), 
    icon=SVGIcon(icon_name="step-backward"))

pause_button = ICleanButton(
    label="", 
    button_type="warning", 
    width=75, 
    margin=(5,1,5,1), 
    icon=SVGIcon(icon_name="pause"))

text_input_iter = TextInput(title="Iterations", value="1", width=120)
text_input_cycles = TextInput(title="Cycles", value="1", width=120)
text_input_threshold = TextInput(title="Threshold", value="0.5", width=120)

mask = PreText(text='', width=380)

image_figure.js_on_event(
    SelectionGeometry, 
    CustomJS(args=dict(
        source=source, 
        box=box, 
        mask=mask), 
        code="""
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

slider = ICleanSlider(
    start=0, 
    end=shape[-1]-1, 
    value=0, 
    step=1, 
    title="Channel", 
    width=380)

callback = CustomJS( 
    args=dict(
        source=source,
        converge_source=converge_source,
        minor_converge_dict=minor_converge_dict, 
        slider=slider), 
    code="""
        source.channel(slider.value);
        converge_source.data = minor_converge_dict[slider.value];
    """)

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
    row(image_figure, column( spectral_figure, converge_figure)))

image_figure.add_layout(box)
show(layout)

start_server = websockets.serve( pipe.process_messages, pipe.address[0], pipe.address[1] )
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()