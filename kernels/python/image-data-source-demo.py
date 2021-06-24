import os
from casagui.bokeh.state import initialize_bokeh
#initialize_bokeh( "casaguijs/dist/casaguijs.min.js" )        ### local build
initialize_bokeh( )                                           ### fetch from https://casa.nrao.edu/
from casagui.bokeh.sources import ImageDataSource, SpectraDataSource, ImagePipe
from bokeh.layouts import column, row
from bokeh.models import Button, CustomJS, Slider, HoverTool
from bokeh.plotting import figure, show

from casagui.utils import find_ws_address

import urllib.request
import tarfile

import asyncio
import websockets

img = 'g35.03_II_nh3_11.hline.image'
url = "https://casa.nrao.edu/download/devel/casavis/data/g35-hline-img.tar.gz"

if not os.path.isdir(img):
    tstream = urllib.request.urlopen(url)
    tar = tarfile.open(fileobj=tstream, mode="r:gz")
    tar.extractall()

pipe = ImagePipe( image=img, address=find_ws_address( ) )
source = ImageDataSource( image_source=pipe )
spectra = SpectraDataSource( image_source=pipe )
shape = pipe.shape( )

pos_cb = CustomJS( args=dict(spectra=spectra),
                   code = """var geometry = cb_data['geometry'];
                             var x_pos = Math.floor(geometry.x);
                             var y_pos = Math.floor(geometry.y);
                             spectra.spectra(x_pos,y_pos)
                          """ )

hover_tool = HoverTool(callback=pos_cb)
fig = figure( plot_height=500, plot_width=500,
              tooltips=[("x", "$x"), ("y", "$y"), ("value", "@d")],
              tools=[ hover_tool, "box_zoom,reset" ] )
fig.x_range.range_padding = fig.y_range.range_padding = 0
fig.image(image="d", x=0, y=0, dw=shape[0], dh=shape[1], palette="Spectral11", level="image", source=source )
fig.grid.grid_line_width = 0.5

sfig = figure(plot_height=110,plot_width=500,title=None, tools=[ ])
sfig.x_range.range_padding = sfig.y_range.range_padding = 0
sfig.line( x='x', y='y', source=spectra )
sfig.grid.grid_line_width = 0.5

hover_tool = HoverTool(callback=pos_cb)
slider = Slider(start=0, end=shape[-1]-1, value=87, step=1, title="Channel")
callback = CustomJS( args=dict( source=source, slider=slider ),
                     code="""source.channel(slider.value)""" )
slider.js_on_change('value', callback)

button_prev = Button(label="prev", max_width=60)
button_next = Button(label="next", max_width=60)
button_prev.js_on_click(
    CustomJS(args=dict(slider=slider), code="""if (slider.value>slider.start) { slider.value = slider.value - 1; }"""))
button_next.js_on_click(
    CustomJS(args=dict(slider=slider), code="""if (slider.value < slider.end) { slider.value = slider.value + 1; }"""))

layout = column( sfig,
                 fig,
                 row(slider, button_prev, button_next) )

show(layout)

start_server = websockets.serve( pipe.process_messages, pipe.address[0], pipe.address[1] )
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
