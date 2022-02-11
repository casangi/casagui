import { ColumnDataSource } from "@bokehjs/models/sources/column_data_source"
import * as p from "@bokehjs/core/properties"
import {uuid4} from "@bokehjs/core/util/string"
import { CallbackLike0 } from "@bokehjs/models/callbacks/callback";
import { ImagePipe } from "./image_pipe"

// Data source where the data is defined column-wise, i.e. each key in the
// the data attribute is a column name, and its value is an array of scalars.
// Each column should be the same length.
export namespace ImageDataSource {
  export type Attrs = p.AttrsOf<Props>

  export type Props = ColumnDataSource.Props & {
      init_script: p.Property<CallbackLike0<ColumnDataSource> | null>;
      image_source: p.Property<ImagePipe>
      num_chans: p.Property<[Number,Number]>          // [ stokes, spectral ]
      cur_chan:  p.Property<[Number,Number]>          // [ stokes, spectral ]
  }
}

export interface ImageDataSource extends ImageDataSource.Attrs {}

export class ImageDataSource extends ColumnDataSource {
    properties: ImageDataSource.Props

    imid: string

    constructor(attrs?: Partial<ImageDataSource.Attrs>) {
        super(attrs);
        this.imid = uuid4( )
    }
    initialize(): void {
        super.initialize();
        const execute = () => {
            if ( this.init_script != null ) this.init_script!.execute( this )
        }
        execute( )
    }
    channel( c: number, s: number = 0, cb?: (msg:{[key: string]: any}) => any ): void {
        this.image_source.channel( [s, c],
                                   (data: any) => {
                                       this.cur_chan = [ s, c ]
                                       if ( cb ) {
                                           cb(data)
                                       }
                                       this.data = data.chan
                                   }, this.imid )
    }
    refresh( cb?: (msg:{[key: string]: any}) => any ): void {
        // supply default index value because the ImagePipe will have no cached
        // index values for this.imid if there have been no updates yet...
        this.image_source.refresh( (data: any) => {
            if ( cb ) { cb(data) }
            this.data = data.chan
        }, this.imid, [ 0, 0 ] )
    }
    static init_ImageDataSource( ): void {
        this.define<ImageDataSource.Props>(({ Tuple, Number, Ref, Any }) => ({
            init_script: [ Any ],
            image_source: [ Ref(ImagePipe) ],
            num_chans: [ Tuple(Number,Number) ],
            cur_chan:  [ Tuple(Number,Number) ],
        }));
    }
}
