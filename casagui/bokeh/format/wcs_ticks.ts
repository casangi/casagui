import { TickFormatter } from "@bokehjs/models/formatters/tick_formatter"
import * as p from "@bokehjs/core/properties"
import { ImageDataSource } from "../sources/image_data_source"

declare global {
    // loaded into "window" by casalib
    interface Window { coordtxl: any }
}

// Data source where the data is defined column-wise, i.e. each key in the
// the data attribute is a column name, and its value is an array of scalars.
// Each column should be the same length.
export namespace WcsTicks {
  export type Attrs = p.AttrsOf<Props>

  export type Props = TickFormatter.Props & {
      axis: p.Property<String>
      image_source: p.Property<ImageDataSource>
  }
}

export interface WcsTicks extends WcsTicks.Attrs {}

export class WcsTicks extends TickFormatter {
    properties: WcsTicks.Props

    constructor(attrs?: Partial<WcsTicks.Attrs>) {
        super(attrs);
    }
    initialize(): void {
        super.initialize();
    }

    // TickFormatters should implement this method, which accepts a list
    // of numbers (ticks) and returns a list of strings
    doFormat( ticks: string[] | number[] ) {
        // format the first tick as-is
        const formatted = [`${ticks[0]}`]
        for (let i = 1, len = ticks.length; i < len; i++) {
            formatted.push(`+${(Number(ticks[i]) - Number(ticks[0])).toPrecision(2)}`)
        }
        return formatted
    }

    static init_WcsTicks( ): void {
        this.define<WcsTicks.Props>(({ Ref, String }) => ({
            axis: [ String ],
            image_source: [ Ref(ImageDataSource) ],
        }));
    }
}
