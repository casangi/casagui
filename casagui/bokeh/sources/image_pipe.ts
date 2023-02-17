import { DataPipe } from "./data_pipe"
import * as p from "@bokehjs/core/properties"

declare var object_id: ( obj: { [key: string]: any } ) => string

// Data source where the data is defined column-wise, i.e. each key in the
// the data attribute is a column name, and its value is an array of scalars.
// Each column should be the same length.
export namespace ImagePipe {
    export type Attrs = p.AttrsOf<Props>

    export type Props = DataPipe.Props & {
        dataid: p.Property<string>
        shape: p.Property<[number,number,number,number]>
        channel: p.Property<( index: [number,number], cb: (msg:{[key: string]: any}) => any, id: string ) => void>
        spectra: p.Property<( index: [number,number,number], cb: (msg:{[key: string]: any}) => any, id: string ) => void>
        refresh: p.Property<( cb: (msg:{[key: string]: any}) => any, id: string, default_index: [number] ) => void>
    }
}

export interface ImagePipe extends ImagePipe.Attrs {}

export class ImagePipe extends DataPipe {
    properties: ImagePipe.Props

    position: {[key: string]: any} = { }

    constructor(attrs?: Partial<ImagePipe.Attrs>) {
        super(attrs);
    }

    // fetch channel
    //    index: [ stokes index, spectral plane ]
    // RETURNED MESSAGE SHOULD HAVE { id: string, message: any }
    channel( index: [number, number], cb: (msg:{[key: string]: any}) => any, id: string ): void {
        this.position[id] = { index }
        let message = { action: 'channel', index, id }
        super.send( this.dataid, message, cb )
    }
    // fetch spectra
    //    index: [ RA index, DEC index, stokes index ]
    // RETURNED MESSAGE SHOULD HAVE { id: string, message: any }
    spectra( index: [number, number, number], cb: (msg:{[key: string]: any}) => any, id: string ) {
        let message = { action: 'spectra', index, id }
        super.send( this.dataid, message, cb )
    }

    refresh( cb: (msg:{[key: string]: any}) => any, id: string, default_index=[ 0, 0 ] as number[] ): void {
        let { index } = id in this.position ? this.position[id] : { index: default_index }
        if ( index.length === 2 ) {
            // refreshing channel
            let message = { action: 'channel', index, id }
            super.send( this.dataid, message, cb )

        } else if ( index.length === 3 ) {
            // refreshing spectra
            let message = { action: 'spectra', index, id }
            super.send( this.dataid, message, cb )
        }
    }

    static init_ImagePipe( ): void {
        this.define<ImagePipe.Props>(({ String, Tuple, Number }) => ({
            dataid: [ String ],
            shape: [Tuple(Number,Number,Number,Number)]
        }));
    }
}
