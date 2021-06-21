import { ColumnDataSource } from "@bokehjs/models/sources/column_data_source"
import * as p from "@bokehjs/core/properties"
import { is_NDArray_ref, decode_NDArray } from "@bokehjs/core/util/serialization"

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
