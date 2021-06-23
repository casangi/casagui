import { ColumnDataSource } from "@bokehjs/models/sources/column_data_source"
import * as p from "@bokehjs/core/properties"
import {uuid4} from "@bokehjs/core/util/string"
import { ImagePipe } from "./image_pipe"

// Data source where the data is defined column-wise, i.e. each key in the
// the data attribute is a column name, and its value is an array of scalars.
// Each column should be the same length.
export namespace ImageDataSource {
  export type Attrs = p.AttrsOf<Props>

  export type Props = ColumnDataSource.Props & {
      image_source: p.Property<ImagePipe>
  }
}

export interface ImageDataSource extends ImageDataSource.Attrs {}

export class ImageDataSource extends ColumnDataSource {
    properties: ImageDataSource.Props

    imid: string

    constructor(attrs?: Partial<ImageDataSource.Attrs>) {
        super(attrs);
        this.imid = uuid4( )
        console.log( 'image data source id:', this.imid )
    }
    initialize(): void {
        super.initialize();
    }
    channel( i: number ): void {
        this.image_source.channel( [0, i], (data: any) => this.data = data, this.imid )
    }
    static init_ImageDataSource( ): void {
        this.define<ImageDataSource.Props>(({ Ref }) => ({
            image_source: [ Ref(ImagePipe) ],
        }));
    }
}
