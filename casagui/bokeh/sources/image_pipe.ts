import { DataSource } from "@bokehjs/models/sources/data_source"
import * as p from "@bokehjs/core/properties"
import { is_NDArray_ref, decode_NDArray } from "@bokehjs/core/util/serialization"
import { CallbackLike0 } from "@bokehjs/models/callbacks/callback";

declare var object_id: ( obj: { [key: string]: any } ) => string

// Data source where the data is defined column-wise, i.e. each key in the
// the data attribute is a column name, and its value is an array of scalars.
// Each column should be the same length.
export namespace ImagePipe {
    export type Attrs = p.AttrsOf<Props>

    export type Props = DataSource.Props & {
        init_script: p.Property<CallbackLike0<DataSource> | null>;
        shape: p.Property<[number,number,number,number]>
        address: p.Property<[string,number]>
        channel: p.Property<( index: [number,number], cb: (msg:{[key: string]: any}) => any, id: string ) => void>
        spectra: p.Property<( index: [number,number,number], cb: (msg:{[key: string]: any}) => any, id: string ) => void>
        refresh: p.Property<( cb: (msg:{[key: string]: any}) => any, id: string, default_index: [number] ) => void>
    }
}

export interface ImagePipe extends ImagePipe.Attrs {}

export class ImagePipe extends DataSource {
    properties: ImagePipe.Props

    websocket: any
    queue: {[key: string]: any} = { }
    pending: {[key: string]: any} = { }
    position: {[key: string]: any} = { }

    constructor(attrs?: Partial<ImagePipe.Attrs>) {
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
                if ( 'id' in data && 'message' in data ) {
                    // 'message' here is generated in python and
                    // contains the requested slice of the image
                    let { id, message }: { id: string, message: any } = data
                    let { cb, index }: { cb: (x: any) => any, index: [ number, ... [number]] } = this.pending[id]
                    delete this.pending[id]
                    if ( id in this.queue ) {
                        // send next message queued by 'id'
                        let {cb, message, index} = this.queue[id]
                        delete this.queue[id]
                        this.pending[id] = { cb, index }
                        this.websocket.send(JSON.stringify(message))
                    }
                    // post message
                    this.position[id] = { index }
                    cb( message )
                } else {
                    console.log( `imagepipe received data without 'id' and/or 'message' field: ${data}` )
                }

            } else {
                console.log("imagepipe received binary data", event.data.byteLength, "bytes" )
            }
        }
        let session = object_id(this)
        this.websocket.onopen = ( ) => {
            this.websocket.send(JSON.stringify({ action: 'initialize', session }))
        }
    }
    initialize(): void {
        super.initialize();
        const execute = () => {
            if ( this.init_script != null ) this.init_script!.execute( this )
        }
        execute( )
    }
    // fetch channel
    //    index: [ stokes index, spectral plane ]
    // RETURNED MESSAGE SHOULD HAVE { id: string, message: any }
    channel( index: [number, number], cb: (msg:{[key: string]: any}) => any, id: string ): void {
        let message = { action: 'channel', index, id, session: object_id(this) }
        if ( id in this.pending ) {
            this.queue[id] = { cb, message, index }
        } else {
            this.websocket.send(JSON.stringify(message))
            this.pending[id] = { cb, index }
        }
    }
    // fetch spectra
    //    index: [ RA index, DEC index, stokes index ]
    // RETURNED MESSAGE SHOULD HAVE { id: string, message: any }
    spectra( index: [number, number, number], cb: (msg:{[key: string]: any}) => any, id: string ) {
        let message = { action: 'spectra', index, id, session: object_id(this) }
        if ( id in this.pending ) {
            this.queue[id] = { cb, message, index }
        } else {
            this.websocket.send(JSON.stringify(message))
            this.pending[id] = { cb, index }
        }
    }

    refresh( cb: (msg:{[key: string]: any}) => any, id: string, default_index=[ ] as number[] ): void {
        let { index } = id in this.position ? this.position[id] : { index: default_index }
        if ( index.length === 2 ) {
            // refreshing channel
            let message = { action: 'channel', index, id, session: object_id(this) }
            if ( id in this.pending ) {
                this.queue[id] = { cb, message, index }
            } else {
                this.websocket.send(JSON.stringify(message))
                this.pending[id] = { cb, index }
            }
        } else if ( index.length === 3 ) {
            // refreshing spectra
            let message = { action: 'spectra', index, id, session: object_id(this) }
            if ( id in this.pending ) {
                this.queue[id] = { cb, message, index }
            } else {
                this.websocket.send(JSON.stringify(message))
                this.pending[id] = { cb, index }
            }
        }
    }

    static init_ImagePipe( ): void {
        this.define<ImagePipe.Props>(({ Tuple, String, Number, Any }) => ({
            init_script: [ Any ],
            address: [Tuple(String,Number)],
            shape: [Tuple(Number,Number,Number,Number)]
        }));
    }
}
