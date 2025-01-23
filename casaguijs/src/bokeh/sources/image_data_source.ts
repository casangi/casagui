import { ColumnDataSource } from "@bokehjs/models/sources/column_data_source"
import * as p from "@bokehjs/core/properties"
import {uuid4} from "@bokehjs/core/util/string"
import { ImagePipe } from "./image_pipe"
import { CallbackLike0 } from "@bokehjs/core/util/callbacks";
import {execute} from "@bokehjs/core/util/callbacks"

declare global { // CASALIB DECL
    var casalib: {
        object_id: ( obj: { [key: string]: any } ) => string
        ReconnectState: ( ) => { timeout: number, retries: number, connected: boolean, backoff: ( ) => void }
        coordtxl: any,
        d3: any
    }
}

// Data source where the data is defined column-wise, i.e. each key in the
// the data attribute is a column name, and its value is an array of scalars.
// Each column should be the same length.
export namespace ImageDataSource {
  export type Attrs = p.AttrsOf<Props>

  export type Props = ColumnDataSource.Props & {
      init_script: p.Property<CallbackLike0<ImageDataSource> | null>;
      image_source: p.Property<ImagePipe>
      _mask_contour_source: p.Property<ColumnDataSource | null>  // source for multi_polygon contours
      num_chans: p.Property<[Number,Number]>                     // [ stokes, spectral ]
      cur_chan:  p.Property<[Number,Number]>                     // [ stokes, spectral ]
  }
}

export interface ImageDataSource extends ImageDataSource.Attrs {}

export class ImageDataSource extends ColumnDataSource {
    declare properties: ImageDataSource.Props

    imid: string
    last_chan: [number, number]

    static __module__ = "casagui.bokeh.sources._image_data_source"

    constructor(attrs?: Partial<ImageDataSource.Attrs>) {
        super(attrs);
        this.imid = uuid4( )
    }

    _mask_contour( mask: any[] ): {[key: string]: any} {
        // converts d3-contours (https://github.com/d3/d3-contour) generated contours into bokeh's multi-polygon format
        function split( pairs: any ) {
            // d3-contours are represented as a list of tuples, but bokeh needs to lists one each of x and y coordinates
            // @ts-ignore: Parameter 'acc' implicitly has an 'any' type.
            return pairs.reduce( (acc, pair) => { acc[0].push(pair[0]); acc[1].push(pair[1]); return acc }, [[],[]] )
        }
        // @ts-ignore:
        const d3contours = casalib.d3.contours( ).size(this.image_source.shape.slice(0,2)).thresholds([1])(mask[0])[0]
        //             Parameter 'x' implicitly has an 'any' type.
        // @ts-ignore: Parameter 'y' implicitly has an 'any' type.
        const split_tuples = d3contours.coordinates.map( x => x.map( y => split(y) ) )
        // @ts-ignore: Parameter 'ps' implicitly has an 'any' type.
        const reformatted = { xs: [ split_tuples.map( ps => ps.map(  x => x[0] ) ) ],
        // @ts-ignore: Parameter 'ps' implicitly has an 'any' type.
                              ys: [ split_tuples.map( ps => ps.map(  y => y[1] ) ) ]  }
        return reformatted
    }

    initialize(): void {
        super.initialize();
        // when an initial mask is supplied by the user, it is included
        // in the data object. In case there is a non-zero mask, we must
        // search for a contour upon initialization...
        if ( this._mask_contour_source != null &&
             'msk' in this.data &&
             this.data.msk.length > 0 &&
            // @ts-ignore: error TS2571: Object ("this.data.msk[0]") is of type 'unknown'.
            this.data.msk[0].length > 0 ) {
            const mask = <Array<any>>this.data.msk
            this._mask_contour_source.data = this._mask_contour( mask )
        }
        if ( typeof(this.last_chan) == 'undefined' ) {
            this.last_chan = [ this.cur_chan[0].valueOf( ), this.cur_chan[1].valueOf( ) ]
        }
        const _execute = () => {
            if ( this.init_script != null ) void execute( this.init_script, this )
        }
        _execute( )
    }

    channel( c: number, s: number = 0, cb?: (msg:{[key: string]: any}) => any ): void {
        this.image_source.channel( [s, c],
                                   (data: any) => {
                                       if ( typeof data === 'undefined' || typeof data.chan === 'undefined' )
                                           console.log( 'ImageDataSource ERROR ENCOUNTERED <1>', data )
                                       this.last_chan = [ this.cur_chan[0].valueOf( ), this.cur_chan[1].valueOf( ) ]
                                       this.cur_chan = [ s, c ]
                                       if ( this._mask_contour_source != null && 'chan' in data && 'msk' in data.chan ) {
                                           data.msk_contour = this._mask_contour( data.chan.msk )
                                           // bokeh does not allow adding extraneous attributes so 'msk_contour' must be outside of 'chan'
                                           this._mask_contour_source.data = data.msk_contour
                                       }
                                       if ( cb ) { cb(data) }
                                       this.data = data.chan
                                   }, this.imid )
    }

    adjust_colormap( bounds: [ number[], number[] ] | string,
                     transfer: {[key: string]: any},
                     cb: (msg:{[key: string]: any}) => any ) {
        this.image_source.adjust_colormap( bounds, transfer, cb, this.imid, true )
    }

    signal_change( ): void {
        this.change.emit( )
    }

    refresh( cb?: (msg:{[key: string]: any}) => any ): void {
        // supply default index value because the ImagePipe will have no cached
        // index values for this.imid if there have been no updates yet...
        this.image_source.refresh( (data: any) => {
            if ( typeof data === 'undefined' || typeof data.chan === 'undefined' )
                console.log( 'ImageDataSource ERROR ENCOUNTERED <2>', data )
            if ( this._mask_contour_source != null && 'chan' in data && 'msk' in data.chan ) {
                data.msk_contour = this._mask_contour( data.chan.msk )
                // bokeh does not allow adding extraneous attributes so 'msk_contour' must be outside of 'chan'
                this._mask_contour_source.data = data.msk_contour
            }
            if ( cb ) { cb(data) }
            this.data = data.chan
        }, this.imid, [ 0, 0 ] )
    }

    wcs( ): {[key: string]: any} | null {
        return this.image_source.wcs( )
    }

    static {
        this.define<ImageDataSource.Props>(({ Tuple, Number, Ref, Nullable, Any }) => ({
            init_script: [ Any, null ],
            image_source: [ Ref(ImagePipe) ],
            _mask_contour_source: [ Nullable(Ref(ColumnDataSource)), null ],
            num_chans: [ Tuple(Number,Number) ],
            cur_chan:  [ Tuple(Number,Number) ],
        }));
    }
}
