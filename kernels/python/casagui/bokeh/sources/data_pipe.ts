import { DataSource } from "@bokehjs/models/sources/data_source"
import * as p from "@bokehjs/core/properties"
import { is_NDArray_ref, decode_NDArray } from "@bokehjs/core/util/serialization"

// Data source where the data is defined column-wise, i.e. each key in the
// the data attribute is a column name, and its value is an array of scalars.
// Each column should be the same length.
export namespace DataPipe {
    export type Attrs = p.AttrsOf<Props>

    export type Props = DataSource.Props & {
        address: p.Property<[string,number]>
        send: p.Property<( id: string, message: {[key: string]: any}, cb: (msg:{[key: string]: any}) => any ) => void>
        register: p.Property<( id: string, cb: (msg:{[key: string]: any}) => any ) => void>

    }
}

export interface DataPipe extends DataPipe.Attrs {}

export class DataPipe extends DataSource {
    properties: DataPipe.Props

    websocket: any
    send_queue: {[key: string]: any} = { }
    pending: {[key: string]: any} = { }
    incoming_callbacks: {[key: string]: any} = { }

    constructor(attrs?: Partial<DataPipe.Attrs>) {
        super(attrs);
        let ws_address = `ws://${this.address[0]}:${this.address[1]}`
        console.log( "imagepipe url:", ws_address )
        this.websocket = new WebSocket(ws_address)
        this.websocket.binaryType = "arraybuffer"
        this.websocket.onmessage = (event: any) => {
            //--- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
            // helper function
            //--- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
            function expand_arrays(obj: any) {
                const res: any = Array.isArray(obj) ? new Array( ) : { }
                for (const key in obj) {
                    let value = obj[key];
                    if( is_NDArray_ref(value) ) {
                        const buffers0 = new Map<string, ArrayBuffer>( )
                        res[key] = decode_NDArray(value,buffers0)
                    } else {
                        res[key] = typeof value === 'object' && value !== null ? expand_arrays(value) : value
                    }
                }
                return res
            }
            //--- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
            if (typeof event.data === 'string' || event.data instanceof String) {
                let obj = JSON.parse( event.data )
                let data = expand_arrays( obj )
                if ( 'id' in data && 'direction' in data && 'message' in data ) {
                    let { id, message, direction }: { id: string, message: any, direction: string} = data
                    if ( direction == 'j2p' ) {
                        if ( id in this.pending ) {
                            let { cb }: { cb: (x:any) => any } = this.pending[id]
                            delete this.pending[id]
                            if ( id in this.send_queue && this.send_queue[id].length > 0 ) {
                                // send next message queued by 'id'
                                let {cb, msg} = this.send_queue[id].shift( )
                                this.pending[id] = { cb }
                                this.websocket.send(JSON.stringify(msg))
                            }
                            // post message
                            cb( message )
                        } else {
                            console.log("message received but could not find id")
                        }
                    } else {
                        if ( id in this.incoming_callbacks ) {
                            let result = this.incoming_callbacks[id](message)
                            this.websocket.send(JSON.stringify({ id, direction, message: result}))
                        }
                    }
                } else {
                    console.log( `datapipe received message without one of 'id', 'message' or 'direction': ${data}` )
                }

            } else {
                console.log("datapipe received binary data", event.data.byteLength, "bytes" )
            }
        }
    }
    initialize(): void {
        super.initialize();
    }

    register( id: string, cb: (msg:{[key: string]: any}) => any ): void {
        this.incoming_callbacks[id] = cb
    }

    send( id: string, message: {[key: string]: any}, cb: (msg:{[key: string]: any}) => any ): void {
        let msg = { id, message, direction: 'j2p' }
        if ( id in this.pending ) {
            if ( id in this.send_queue ) {
                this.send_queue[id].push( { cb, msg } )
            } else {
                this.send_queue[id] = [ { cb, msg } ]
            }
        } else {
            if ( id in this.send_queue && this.send_queue[id].length > 0 ) {
                this.send_queue[id].push( { cb, msg } )
                {   // seemingly cannot reference wider 'cb' and the block-scoped
                    // 'cb' within the same block...
                    // src/bokeh/sources/data_pipe.ts:100:45 - error TS2448: Block-scoped variable 'cb' used before its declaration.
                    let { cb, msg } = this.send_queue[id].shift( )
                    this.pending[id] = { cb }
                    this.websocket.send(JSON.stringify(msg))
                }
            } else {
                this.pending[id] = { cb }
                this.websocket.send(JSON.stringify(msg))
            }
        }
    }

    static init_DataPipe( ): void {
        this.define<DataPipe.Props>(({ Tuple, String, Number }) => ({
            address: [Tuple(String,Number)],
        }));
    }
}
