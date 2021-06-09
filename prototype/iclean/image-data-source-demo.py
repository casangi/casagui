import os
import numpy as np
from bokeh.layouts import column, row
from bokeh.models import Button, CustomJS, Slider
from bokeh.plotting import ColumnDataSource, figure, show
from casatools import image as imagetool
from bokeh.util.compiler import JavaScript
from bokeh.util.serialization import transform_column_source_data

import urllib.request
import tarfile

from socket import socket
import asyncio
import websockets
import json

img = 'g35.03_II_nh3_11.hline.image'
url = "https://casa.nrao.edu/download/devel/casavis/data/g35-hline-img.tar.gz"

if not os.path.isdir(img):
    tstream = urllib.request.urlopen(url)
    tar = tarfile.open(fileobj=tstream, mode="r:gz")
    tar.extractall()

def find_ws_address( ):
    sock = socket( )
    sock.bind(('127.0.0.1',0))
    result = sock.getsockname( )
    sock.close( )
    return result

class ImageDataSource(ColumnDataSource):
    __im_path = None
    __im = None
    __im_indexes = None            ### perhaps down the road we will want to display
                                   ### only a subset of the planes of the image
    __chan_shape = None

    address = find_ws_address( )

    __implementation__ = JavaScript("""import { ColumnDataSource } from "models/sources/column_data_source"
import { UpdateMode } from "core/enums"
import { is_NDArray_ref, decode_NDArray } from "core/util/serialization"

export class ImageDataSource extends ColumnDataSource {
    constructor(attrs) {
        super(attrs);
        this.ws_address = "%s"
        console.log( "websocket url:", this.ws_address )
        this.websocket = new WebSocket(this.ws_address)
        this.websocket.binaryType = "arraybuffer"
        this.websocket.onmessage = (event) => {
            function expand_arrays(obj) {
                const res = Array.isArray(obj) ? new Array( ) : { }
                for (const key in obj) {
                    let value = obj[key];
                    if( is_NDArray_ref(value) ) {
                        res[key] = decode_NDArray(value)
                    } else {
                        res[key] = expand_arrays(value)
                    }
                }
                return res
            }
            if (typeof event.data === 'string' || event.data instanceof String) {
                let obj = JSON.parse( event.data )
                let data = expand_arrays( obj )
                this.data = data
            } else {
                console.log("binary data", event.data.byteLength, "bytes" )
            }
        }
    }
    initialize() {
        super.initialize();
    }
    channel( i ) {
        this.websocket.send(JSON.stringify({ action: 'channel', value: i }))
    }
    static init_ImageDataSource() {
        /******IT IS NOT CLEAR WHAT THIS DOES FOR WebDataSource************************************************/
        /******https://github.com/bokeh/bokeh/blob/main/bokehjs/src/lib/models/sources/web_data_source.ts******/
        /******MAYBE SHARING DATA BETWEEN PYTHON AND JAVASCRIPT?***********************************************/
        this.define(({ Any, Int, String, Nullable }) => ({
            max_size: [Nullable(Int), null],
            mode: [UpdateMode, "replace"],
            adapter: [Nullable(Any /*TODO*/), null],
            data_url: [String],
        }));
    }
}
ImageDataSource.__name__ = "ImageDataSource";
ImageDataSource.init_ImageDataSource();
""" % ("ws://%s:%d/" % address))

    def shape( self ):
        return self.__chan_shape + [ len(self.__im_indexes) ]
    def channel( self, index, image=None ):
        print("\t>>>>---> fetching %d" % index)
        if image is not None:
            self.__im = imagetool( )
            try:
                self.__im.open(image)
            except:
                self.__im = None
        if self.__im is None:
            raise RuntimeError('no available image')
        s = self.__im.shape( )
        self.__chan_shape = list(s[0:2])
        if len(s) > 2:
            self.__im_indexes = range(0,s[-1])
        elif len(s) == 2:
            self.__im_indexes = range(0,1)
        return np.squeeze( self.__im.getchunk( blc=[0,0,0,self.__im_indexes[index]],
                                               trc=self.__chan_shape + [0,self.__im_indexes[index]]) ).transpose( )

    def __init__( self, image, *args, **kwargs ):
        super( ).__init__( self, data={ 'd': [ self.channel( 87, image ) ] }, *args, **kwargs )

    async def process_messages( self, websocket, path ):
        count = 1
        async for message in websocket:
            cmd = json.loads(message)
            chan = self.channel(cmd['value'])
            msg = transform_column_source_data( { 'd': [ chan ] } )
            await websocket.send(json.dumps(msg))
            count += 1

source = ImageDataSource( image=img )
shape = source.shape( )

fig = figure(tooltips=[("x", "$x"), ("y", "$y"), ("value", "@image")])
fig.x_range.range_padding = fig.y_range.range_padding = 0
fig.image(image="d", x=0, y=0, dw=shape[0], dh=shape[1], palette="Spectral11", level="image", source=source )
fig.grid.grid_line_width = 0.5

slider = Slider(start=0, end=shape[2]-1, value=87, step=1, title="Channel")
callback = CustomJS( args=dict( source=source, slider=slider ),
                     code="""source.channel(slider.value)""" )
slider.js_on_change('value', callback)

button_prev = Button(label="prev", max_width=60)
button_next = Button(label="next", max_width=60)
button_prev.js_on_click(
    CustomJS(args=dict(slider=slider), code="""if (slider.value>slider.start) { slider.value = slider.value - 1; }"""))
button_next.js_on_click(
    CustomJS(args=dict(slider=slider), code="""if (slider.value < slider.end) { slider.value = slider.value + 1; }"""))

layout = column(fig,
                row(slider, button_prev, button_next)
                )

show(layout)

start_server = websockets.serve( source.process_messages, source.address[0], source.address[1] )
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
