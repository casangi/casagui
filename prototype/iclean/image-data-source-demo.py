import os
import numpy as np
from bokeh.layouts import column, row
from bokeh.models import Button, CustomJS, Slider
from bokeh.plotting import ColumnDataSource, figure, show
from casatools import image as imagetool
from bokeh.util.compiler import TypeScript
from bokeh.util.serialization import transform_column_source_data
from bokeh.core.properties import Tuple, String, Int

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

    address = Tuple( String, Int, help="two integer sequence representing the address and port to use for the websocket" )

    __implementation__ = TypeScript("""import { ColumnDataSource } from "models/sources/column_data_source"
import * as p from "core/properties"
import { is_NDArray_ref, decode_NDArray } from "core/util/serialization"

// Data source where the data is defined column-wise, i.e. each key in the
// the data attribute is a column name, and its value is an array of scalars.
// Each column should be the same length.
export namespace ImageDataSource {
  export type Attrs = p.AttrsOf<Props>

  export type Props = ColumnDataSource.Props & {
    address: p.Property<[string,number]>
  }
}

export interface ImageDataSource extends ImageDataSource.Attrs {}

export class ImageDataSource extends ColumnDataSource {
    properties: ImageDataSource.Props
    websocket: any

    constructor(attrs?: Partial<ImageDataSource.Attrs>) {
        super(attrs);
        let ws_address = `ws://${this.address[0]}:${this.address[1]}`
        console.log( "websocket url:", ws_address )
        this.websocket = new WebSocket(ws_address)
        this.websocket.binaryType = "arraybuffer"
        this.websocket.onmessage = (event: any) => {
            function expand_arrays(obj: any) {
                const res: any = Array.isArray(obj) ? new Array( ) : { }
                for (const key in obj) {
                    let value = obj[key];
                    if( is_NDArray_ref(value) ) {
                        const buffers0 = new Map<string, ArrayBuffer>( )
                        res[key] = decode_NDArray(value,buffers0)
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
    initialize(): void {
        super.initialize();
    }
    channel( i: number ): void {
        this.websocket.send(JSON.stringify({ action: 'channel', value: i }))
    }
    static init_ImageDataSource( ): void {
        this.define<ImageDataSource.Props>(({ Tuple, String, Number }) => ({
            address: [Tuple(String,Number)],
        }));
    }
}
""" )

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

source = ImageDataSource( image=img, address=find_ws_address( ) )
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
