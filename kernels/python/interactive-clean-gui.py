import os
import numpy as np
import bokeh
from uuid import uuid4

from bokeh.layouts import column, row, Spacer
from bokeh.models import CustomJS, Slider, RadioButtonGroup, TextInput, Button, MultiChoice
from bokeh.models import BoxAnnotation, PreText, Range1d, LinearAxis, Span, HoverTool, DataTable, TableColumn
from bokeh.events import SelectionGeometry
from bokeh.plotting import ColumnDataSource, figure, show

from casagui.bokeh.state import initialize_bokeh
#initialize_bokeh( "casaguijs/dist/casaguijs.min.js" )        ### local build
initialize_bokeh( )                                           ### fetch from https://casa.nrao.edu/
from casagui.bokeh.sources import ImageDataSource, SpectraDataSource, ImagePipe, DataPipe
from casagui.bokeh.components.button.iclean_button import ICleanButton
from casagui.bokeh.components.slider.iclean_slider import ICleanSlider
from casagui.bokeh.components.custom_icon.svg_icon import SVGIcon

from casatools import image
from casatasks import tclean, imstat

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

#img = 'g35.03_II_nh3_11.hline.image'
img = 'test.image'
output_image = 'test'

rec = tclean(
    vis='refim_point_withline.ms', 
    imagename=output_image, 
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

cont_id = str(uuid4())

data_pipe = DataPipe(address=find_ws_address())

image_pipe = ImagePipe(image=img, address=find_ws_address())
source = ImageDataSource(image_source=image_pipe)
spectra = SpectraDataSource(image_source=image_pipe)
shape = image_pipe.shape()

pos_cb = CustomJS(args=dict(spectra=spectra),
                   code = """var geometry = cb_data['geometry'];
                             var x_pos = Math.floor(geometry.x);
                             var y_pos = Math.floor(geometry.y);
                             spectra.spectra(x_pos,y_pos)
                          """ )

hover_tool = HoverTool(callback=pos_cb)

spectral_figure = figure(
    plot_height=200, 
    plot_width=650, 
    title=None, 
    tools=[])

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
        converge_source.data['flux'].max()*1.5
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

image_figure.plot_height = 600
image_figure.plot_width = 600

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

# TClean Controls
vis = TextInput(
    value="select ms file ...", 
    title="Vis", 
    width=190)

image_name = TextInput(
    value="output file name ...", 
    title="Imagename", 
    width=190)

imsize = TextInput(
    value="100", 
    title="Imsize", 
    width=120)

cell = TextInput(
    value="8.0arcsec", 
    title="Cell", 
    width=120)

specmode = TextInput(
    value="cube", 
    title="Specmode", 
    width=120)

start = TextInput(
    value="1.0GHz", 
    title="Start", 
    width=120)

width = TextInput(
    value="0.1GHz", 
    title="Width",
    width=120)

number_chan = TextInput(
    value="10", 
    title="Number of channels", 
    width=120)

OPTIONS = [('I', 'I'), ('Q', 'Q'), ('U', 'U'), ('V', 'V')]
stokes = MultiChoice(
    value=["I"], 
    title="Stokes", 
    options=OPTIONS, 
    width=360)

deconvolver = TextInput(
    value="hogbom", 
    title="Deconvolver", 
    width=120)

gain = TextInput(
    value="0.1", 
    title="Gain", 
    width=120)


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

text_input_iter = TextInput(
    title="Iterations", 
    value="1", 
    width=90)

text_input_cycles = TextInput(
    title="Cycles", 
    value="1", 
    width=90)

text_input_threshold = TextInput(
    title="Threshold", 
    value="0.1Jy", 
    width=90)

text_cycle_factor = TextInput(
    value="20", 
    title="Cycle factor", 
    width=90)

coordinates = ColumnDataSource({
    'coordinates': ['x0', 'x1', 'y0', 'y1'],
    'values':[0, 0, 0, 0]
})

columns = [
        TableColumn(field="coordinates", title="Coordinates"),
        TableColumn(field="values", title="Values"),
    ]
mask = DataTable(source=coordinates, columns=columns, width=380, height=300)

image_stats = imstat(imagename=img)

stats = ColumnDataSource({
    'statistics': [
        'image', 
        'npoints', 
        'sum', 
        'flux', 
        'mean', 
        'stdev', 
        'min', 
        'max', 
        'rms'
    ],
    'values': [
        img, 
        image_stats['npts'][0], 
        image_stats['sum'][0],
        image_stats['flux'][0],
        image_stats['mean'][0],
        image_stats['sigma'][0],
        image_stats['min'][0],
        image_stats['max'][0],
        image_stats['rms'][0],
    ]
})

stats_column = [
    TableColumn(field='statistics', title='Statistics'),
    TableColumn(field='values', title='Values'),
]

stats_table = DataTable(source=stats, columns=stats_column, width=580, height=200)

image_figure.js_on_event(
    SelectionGeometry, 
    CustomJS(args=dict(
        source=source, 
        box=box, 
        mask=coordinates), 
        code="""
            const geometry = cb_obj['geometry'];
            const data = source.data;
            console.log(geometry);
    
            box['left'] = geometry['x0'];
            box['right'] = geometry['x1'];
            box['top'] = geometry['y0'];
            box['bottom'] = geometry['y1'];

            mask.data['values'][0] = Math.floor(geometry['x0']); 
            mask.data['values'][1] = Math.floor(geometry['x1']);  
            mask.data['values'][2] = Math.floor(geometry['y0']);
            mask.data['values'][3] = Math.floor(geometry['y1']);

            console.log(mask.data);

            mask.change.emit();
            source.change.emit();
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
        figure=converge_figure, 
        slider=slider), 
    code="""
        source.channel(slider.value);
        converge_source.data = minor_converge_dict[slider.value];
        
        figure.extra_y_ranges['flux'].end = 1.5*Math.max(...converge_source.data['flux'])
        figure.extra_y_ranges['flux'].start = 0.5*Math.min(...converge_source.data['flux'])
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
            text_cycle_factor,
            text_input_threshold),
        slider, 
        Spacer(width=380, height=30, sizing_mode='scale_width'),
        row(vis, image_name),
        Spacer(width=380, height=30, sizing_mode='scale_width'),
        stokes,
        row(imsize, cell, specmode),
        row(specmode, start, width),            
        row(deconvolver, number_chan, gain),
        Spacer(width=380, height=70, sizing_mode='scale_width'),
        mask), 
    row(
        column(
            image_figure, 
            stats_table
        ), 
        column(
            spectral_figure, 
            converge_figure
        )
    ))

image_figure.add_layout(box)
show(layout)

try:
    async def async_loop( f1, f2 ):
        res = await asyncio.gather(  f1, f2 )

    image_server = websockets.serve( image_pipe.process_messages, image_pipe.address[0], image_pipe.address[1] )
    data_server = websockets.serve( data_pipe.process_messages, data_pipe.address[0], data_pipe.address[1] )
    asyncio.get_event_loop().run_until_complete(async_loop(data_server, image_server))
    asyncio.get_event_loop().run_forever()

except KeyboardInterrupt:
    print('\nInterrupt received, shutting down ...')
    os.system('rm -rf {output_image}.* *.html *.log'.format(output_image=output_image))
