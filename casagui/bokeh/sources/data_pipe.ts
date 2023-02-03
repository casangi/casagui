import { DataSource } from "@bokehjs/models/sources/data_source"
import * as p from "@bokehjs/core/properties"
import { is_NDArray_ref, decode_NDArray } from "@bokehjs/core/util/serialization"
import { CallbackLike0 } from "@bokehjs/models/callbacks/callback";

// global object_id function supplied by casalib
declare var object_id: ( obj: { [key: string]: any } ) => string
declare var ReconnectState: ( ) => { timeout: number, retries: number, connected: boolean, backoff: ( ) => void }

declare global {
    // extend document with our properties
    interface Document { shutdown_in_progress_: boolean }
}


// Data source where the data is defined column-wise, i.e. each key in the
// the data attribute is a column name, and its value is an array of scalars.
// Each column should be the same length.
export namespace DataPipe {
    export type Attrs = p.AttrsOf<Props>

    export type Props = DataSource.Props & {
        init_script: p.Property<CallbackLike0<DataSource> | null>;
        address: p.Property<[string,number]>
    }
}

export interface DataPipe extends DataPipe.Attrs {}

export class DataPipe extends DataSource {
    properties: DataPipe.Props

    websocket: any
    // used to queue up messages sent to a particular id which already has outstanding
    // messages for wwhich a reply has not been received.
    send_queue: {[key: string]: any} = { }
    // used to queue up messages which are sent BEFORE the connection is completely
    // established. After the connection is established, these message are resent in order.
    connection_queue: [ object, [ string, {[key: string]: any}, (msg:{[key: string]: any}) => any ] ][ ] = [ ]
    pending: {[key: string]: any} = { }
    incoming_callbacks: {[key: string]: any} = { }

    constructor(attrs?: Partial<DataPipe.Attrs>) {
        super(attrs);
        let ws_address = `ws://${this.address[0]}:${this.address[1]}`
        console.log( "datapipe url:", ws_address )

        var reconnections: any | undefined = undefined
        document.shutdown_in_progress_ = false

        var connect_to_server = ( ) => {
            if ( this.websocket !== undefined ) {
                this.websocket.close( )
            }

            this.websocket = new WebSocket(ws_address)
            this.websocket.binaryType = "arraybuffer"

            this.websocket.onerror = ( e: any ) => {
                console.log( 'error encountered:', e )
            }

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
                                this.websocket.send( JSON.stringify({ id, direction, message: result, session: object_id(this) }))
                            }
                        }
                    } else {
                        console.log( `datapipe received message without one of 'id', 'message' or 'direction': ${data}` )
                    }

                } else {
                    console.log("datapipe received binary data", event.data.byteLength, "bytes" )
                }
            }

            this.websocket.onopen = ( ) => {
                if ( ! reconnections ) {
                    this.websocket.send(JSON.stringify({ id: 'initialize', direction: 'j2p', session: object_id(this) }))
                } else if ( reconnections.connected == false ) {
                    console.log( `connection reestablished at ${new Date( )}` )
                }
                reconnections = new (ReconnectState as any)( )

                // if there were send events before the websocket was connected, resend them
                while ( this.connection_queue.length > 0 ) {
                    let state = this.connection_queue.shift( )!
                    this.send.apply( state[0], state[1] )
                }
            }

            this.websocket.onclose = ( ) => {
                if ( reconnections.connected == true ) {
                    console.log( `connection lost at ${new Date( )}` )
                    reconnections.connected = false
                    if ( ! document.shutdown_in_progress_ ) {
                        console.log( `connection lost at ${new Date( )}` )
                        var recon = reconnections
                        function reconnect( tries: number ) {
                            if ( reconnections.connected == false ) {
                                console.log( `${tries+1}\treconnection attempt ${new Date( )}` )
                                connect_to_server( )
                                recon.backoff( )
                                if ( recon.retries > 0 ) { setTimeout( reconnect, recon.timeout, tries+1 ) }
                                else if ( reconnections.connected == false ) { console.log( `aborting reconnection after ${tries} attempts ${new Date( )}` ) }
                            }
                        }
                        reconnect( 0 )
                    }
                }
            }
        }
        connect_to_server( )
    }
    initialize(): void {
        super.initialize();
        const execute = () => {
            if ( this.init_script != null ) this.init_script!.execute( this )
        }
        execute( )
    }

    register( id: string, cb: (msg:{[key: string]: any}) => any ): void {
        this.incoming_callbacks[id] = cb
    }

    send( id: string, message: {[key: string]: any}, cb: (msg:{[key: string]: any}) => any ): void {
        let msg = { id, message, direction: 'j2p', session: object_id(this) }
        if ( id in this.pending ) {
            if ( id in this.send_queue ) {
                this.send_queue[id].push( { cb, msg } )
            } else {
                this.send_queue[id] = [ { cb, msg } ]
            }
        } else {
            if ( this.websocket.readyState === WebSocket.CONNECTING ) {
                // connection not yet established yet...
                this.connection_queue.push( [ this, [ id, message, cb ] ] )
            } else if ( id in this.send_queue && this.send_queue[id].length > 0 ) {
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
        this.define<DataPipe.Props>(({ Tuple, String, Number, Any }) => ({
            init_script: [ Any ],
            address: [Tuple(String,Number)],
        }));
    }
}
