import { TickFormatter } from "@bokehjs/models/formatters/tick_formatter"
import * as p from "@bokehjs/core/properties"
import { ImageDataSource } from "../sources/image_data_source"

declare global {  // CASALIB DECL
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
export namespace WcsTicks {
  export type Attrs = p.AttrsOf<Props>

  export type Props = TickFormatter.Props & {
      axis: p.Property<String>
      image_source: p.Property<ImageDataSource>
  }
}

export interface WcsTicks extends WcsTicks.Attrs {}

export class WcsTicks extends TickFormatter {
    declare properties: WcsTicks.Props

    _axis: string | null = null
    _coord: string = "world"

    static __module__ = "casagui.bokeh.format._wcs_ticks"

    constructor(attrs?: Partial<WcsTicks.Attrs>) {
        super(attrs);
    }
    initialize(): void {
        super.initialize()
        if ( this.axis == "x" || this.axis == "X" ||
             this.axis == 'y' || this.axis == "Y" ) {
            this._axis = this.axis == "x" || this.axis == "X" ? "x" : "y"
        } else {
            console.log( "ERROR: WcsTicks formatter created with invalid axis:", this.axis )
        }
    }

    // TickFormatters should implement this method, which accepts a list
    // of numbers (ticks) and returns a list of strings
    doFormat( ticks: string[] | number[] ) {
        const formatted = [ ]
        if ( this._axis && this.image_source.wcs( ) && this._coord == "world" ) {
            for (let i = 0, len = ticks.length; i < len; i++) {
                if ( this._axis == "x" ) {
                    const pt = new casalib.coordtxl.Point2D(Number(ticks[i]),0.0)
                    // @ts-ignore: Object is possibly 'null'... check is above
                    this.image_source.wcs( ).imageToWorldCoords(pt,false)
                    // unicode degrees symbol is "\u00B0"
                    formatted.push( new casalib.coordtxl.WorldCoords(pt.getX(),pt.getY()).format(2000)[0] )
                } else {
                    const pt = new casalib.coordtxl.Point2D(0.0,Number(ticks[i]))
                    // @ts-ignore: Object is possibly 'null'... check is above
                    this.image_source.wcs( ).imageToWorldCoords(pt,false)
                    formatted.push( new casalib.coordtxl.WorldCoords(pt.getX(),pt.getY()).format(2000)[1] )
                }
            }
        } else {
            for (let i = 0, len = ticks.length; i < len; i++) {
                formatted.push('' + ticks[i])
            }
        }
        return formatted
    }

    coordinates( coord: string ) : string {
        if ( coord != this._coord ) {
            //----------------------------------------------------------------------
            // If at some point we want to change the "pixel" orientation of the
            // X axis back to horizontal, we would add a signal that is emitted
            // when "this._axis == 'x'" which could then be linked to setting
            // "major_label_orientation" in the "axis" this class is the "formatter".
            //----------------------------------------------------------------------
            if ( coord == "world" || coord == "pixel" )
                this._coord = coord
        }
        return this._coord
    }

    static {
        this.define<WcsTicks.Props>(({ Ref, String }) => ({
            axis: [ String ],
            image_source: [ Ref(ImageDataSource) ],
        }));
    }
}
