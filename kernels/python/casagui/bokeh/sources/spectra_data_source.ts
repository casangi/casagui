import { ColumnDataSource } from "@bokehjs/models/sources/column_data_source"
import * as p from "@bokehjs/core/properties"
import {uuid4} from "@bokehjs/core/util/string"
import { ImagePipe } from "./image_pipe"

// Data source where the data is defined column-wise, i.e. each key in the
// the data attribute is a column name, and its value is an array of scalars.
// Each column should be the same length.
export namespace SpectraDataSource {
  export type Attrs = p.AttrsOf<Props>

  export type Props = ColumnDataSource.Props & {
      image_source: p.Property<ImagePipe>
  }
}

export interface SpectraDataSource extends SpectraDataSource.Attrs {}

export class SpectraDataSource extends ColumnDataSource {
    properties: SpectraDataSource.Props

    imid: string

    constructor(attrs?: Partial<SpectraDataSource.Attrs>) {
        super(attrs);
        this.imid = uuid4( )
        console.log( 'spectra data source id:', this.imid )
    }
    initialize(): void {
        super.initialize();
    }
    spectra( r: number, d: number, s: number = 0 ): void {
        this.image_source.spectra( [r, d, s], (data: any) => this.data = data, this.imid )
    }
    static init_SpectraDataSource( ): void {
        this.define<SpectraDataSource.Props>(({ Ref }) => ({
            image_source: [ Ref(ImagePipe) ],
        }));
    }
}
