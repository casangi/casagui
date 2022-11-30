import {PanEvent} from "@bokehjs/core/ui_events"
import {AttrsOf, Property} from "@bokehjs/core/properties"
import {Interval} from "@bokehjs/core/types"
import {BoxZoomTool, BoxZoomToolView} from "@bokehjs/models/tools/gestures/box_zoom_tool"
import { DownsampleState } from "../models/downsample_state"

export class ImageBoxZoomToolView extends BoxZoomToolView {
    override model: ImageBoxZoomTool

    override _pan_start(ev: PanEvent): void {
        console.group("ImageBoxZoom: _pan_start")
        console.trace( )
        console.log(ev)
        super._pan_start(ev)
        console.groupEnd( )
    }
    override _pan_end(e: PanEvent): void {
    	console.group("ImageBoxZoom: _pan_end")
        console.trace( )
        console.log( e )
        console.log( this.plot_view.frame.bbox )
        super._pan_end(e)
        console.groupEnd( )
    }
    override _update([sx0,sx1]: [number,number], [sy0,sy1]: [number,number]): void {
        console.group("ImageBoxZoom: _update")
        console.log(Object.getOwnPropertyNames(this.model.downsample_state))
        console.log(this.model.downsample_state)
        console.log(this.model.downsample_state.shape)
        console.log(this.model.downsample_state.raw)
        console.log(this.model.downsample_state.sampled)
        console.log(this.model.downsample_state.viewport)
        console.log(this.model.downsample_state.connect)
        //casagui/bokeh/components/svg_icon.ts:    this.connect(this.model.change, () => this.render())
        //console.log(this.model.downsample_state.viewport.change)
        console.trace( )
        console.log([sx0,sx1])
        console.log([sy0,sy1])
        if (Math.abs(sx1 - sx0) > 5 || Math.abs(sy1 - sy0) > 5) {
            // box_zoom_tool.ts throws away all zooms of 5 or less screen pixels
            const {x_scales, y_scales} = this.plot_view.frame

            let count: number = 0
            const xrs: Map<string, Interval> = new Map()
            for (const [name, scale] of x_scales) {
                count = count + 1
                const [start, end] = scale.r_invert(sx0, sx1)
                console.log(`x${count}`,name,scale,scale.r_invert)
                console.log(`x${count}`,[start,end])
                xrs.set(name, {start, end})
            }

            const yrs: Map<string, Interval> = new Map()
            for (const [name, scale] of y_scales) {
                count = count + 1
                const [start, end] = scale.r_invert(sy0, sy1)
                console.log(`y${count}`,name,scale,scale.r_invert)
                console.log(`y${count}`,[start,end])
                yrs.set(name, {start, end})
            }

            const zoom_info = {xrs, yrs}
            console.log(zoom_info)
            const xr = xrs.get('default')
            const yr = yrs.get('default')
            if ( xr && yr ) {
                console.log( `xr dist: ${xr.start - xr.end}` )
                console.log( `yr dist: ${yr.start - yr.end}` )
                console.log( `xs dist: ${sx1 - sx0}` )
                console.log( `ys dist: ${sy1 - sy0}` )
            } else {
                console.log( 'xr and/or yr were not found' )
            }
        }
        console.log(this.plot_view)
        this.model.downsample_state.viewport = [[Math.floor(sx0),Math.floor(sy0)],[Math.ceil(sx1),Math.ceil(sy1)]]
        super._update([sx0,sx1],[sy0,sy1])
        console.groupEnd( )
    }
}

export namespace ImageBoxZoomTool {
    export type Attrs = AttrsOf<Props>

    export type Props = BoxZoomTool.Props & {
        downsample_state: Property<DownsampleState>
    }
}

export interface ImageBoxZoomTool extends ImageBoxZoomTool.Attrs {}

export class ImageBoxZoomTool extends BoxZoomTool {
    override properties: ImageBoxZoomTool.Props
    override __view_type__: ImageBoxZoomToolView

    constructor(attrs?: Partial<ImageBoxZoomTool.Attrs>) {
        super(attrs)
    }

    static {
        this.prototype.default_view = ImageBoxZoomToolView
        this.define<ImageBoxZoomTool.Props>(({ Any }) => ({
            downsample_state: [ Any ]
        }))

        //this.register_alias("box_zoom", () => new BoxZoomTool({dimensions: "both"}))
        //this.register_alias("xbox_zoom", () => new BoxZoomTool({dimensions: "width"}))
        //this.register_alias("ybox_zoom", () => new BoxZoomTool({dimensions: "height"}))
    }

    override tool_name: "Image Box Zoom"
}
