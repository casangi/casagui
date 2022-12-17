import {PanEvent} from "@bokehjs/core/ui_events"
import {AttrsOf} from "@bokehjs/core/properties"
//import {Property} from "@bokehjs/core/properties"
import {Interval} from "@bokehjs/core/types"
import {BoxZoomTool, BoxZoomToolView} from "@bokehjs/models/tools/gestures/box_zoom_tool"
//import {Signal} from "@bokehjs/core/signaling"
import {ModelEvent} from "@bokehjs/core/bokeh_events"
//import {Signal} from "@bokehjs/core/signaling"
//import {disconnect} from "@bokehjs/core/signaling"


export class DownsampleZoomEvent extends ModelEvent {
    override event_name: string = "downsample-zoom"

    constructor( readonly blc: [number,number], readonly trc: [number,number] ) {
	super()
    }
}

export class DownsampleBoxZoomToolView extends BoxZoomToolView {
    override model: DownsampleBoxZoomTool

    override _pan_start(ev: PanEvent): void {
        super._pan_start(ev)
    }
    override _pan_end(e: PanEvent): void {
        super._pan_end(e)
    }
    override _update([sx0,sx1]: [number,number], [sy0,sy1]: [number,number]): void {
        if (Math.abs(sx1 - sx0) > 5 || Math.abs(sy1 - sy0) > 5) {
            // box_zoom_tool.ts throws away all zooms of 5 or less screen pixels

            const {x_scales, y_scales} = this.plot_view.frame

            let count: number = 0
            const xrs: Map<string, Interval> = new Map()
            for (const [name, scale] of x_scales) {
                count = count + 1
                const [start, end] = scale.r_invert(sx0, sx1)
                xrs.set(name, {start, end})
            }

            const yrs: Map<string, Interval> = new Map()
            for (const [name, scale] of y_scales) {
                count = count + 1
                const [start, end] = scale.r_invert(sy0, sy1)
                yrs.set(name, {start, end})
            }
            console.log('DownsampleZoomToolView::_update(...)')
            const zoom_info = {xrs, yrs}
            this.plot_view.state.push("box_zoom", {range: zoom_info})
            this.plot_view.update_range(zoom_info)
        }
    }
/*
            const xr = xrs.get('default')
            const yr = yrs.get('default')

            if ( xr && yr ) {
                //console.log('this.plot_view.model.x_range',this.plot_view.model.x_range)
                //console.log('this.plot_view.model.y_range',this.plot_view.model.y_range)
                //this.plot_view.model.x_range.start = Math.min(xr.start,xr.end)
                //this.plot_view.model.x_range.end = Math.max(xr.start,xr.end)
                //this.plot_view.model.y_range.start = Math.min(yr.start,yr.end)
                //this.plot_view.model.y_range.end = Math.max(yr.start,yr.end)
                //const zoom_info = {xrs, yrs}
                //this.plot_view.update_range(zoom_info)


                 // @ts-ignore
                if ( ! this._zoomed_blc || ! this._zoomed_trc ) {
                    // @ts-ignore
                    this._zoomed_x_range = [this.plot_view.model.x_range.start,this.plot_view.model.x_range.end]
                    // @ts-ignore
                    this._zoomed_y_range = [this.plot_view.model.y_range.start,this.plot_view.model.y_range.end]
                    // @ts-ignore
                    this._zoomed_blc = [ Math.min(xr.start,xr.end), Math.min(yr.start,yr.end) ]
                    // @ts-ignore
                    this._zoomed_trc = [ Math.max(xr.start,xr.end), Math.max(yr.start,yr.end) ]
                    console.group('INITAL VALUES FOR ZOOM STATE')
                    // @ts-ignore
                    console.log( 'x range', this._zoomed_x_range )
                    // @ts-ignore
                    console.log( 'y range', this._zoomed_y_range )
                    // @ts-ignore
                    console.log( 'blc', this._zoomed_blc )
                    // @ts-ignore
                    console.log( 'trc', this._zoomed_trc )
                    console.log( [ Math.min(xr.start,xr.end), Math.min(yr.start,yr.end) ] )
                    console.log( [ Math.max(xr.start,xr.end), Math.max(yr.start,yr.end) ] )
                    console.groupEnd( )

	                //this.model.trigger_event( new DownsampleZoomEvent( [ Math.min(xr.start,xr.end), Math.min(yr.start,yr.end) ],
                    //                                                   [ Math.max(xr.start,xr.end), Math.max(yr.start,yr.end) ] ) )
                } else {
                    console.group('SUBSEQUENT VALUES FOR ZOOM STATE')
                    // @ts-ignore
                    console.log( 'x range', this._zoomed_x_range )
                    // @ts-ignore
                    console.log( 'y range', this._zoomed_y_range )
                    // @ts-ignore
                    console.log( 'blc', this._zoomed_blc )
                    // @ts-ignore
                    console.log( 'trc', this._zoomed_trc )
                    console.log( [ Math.min(xr.start,xr.end), Math.min(yr.start,yr.end) ] )
                    console.log( [ Math.max(xr.start,xr.end), Math.max(yr.start,yr.end) ] )

                    // @ts-ignore
                    let newblc01 = [ this._zoomed_blc[0] + Math.min(xr.start,xr.end) * ((this._zoomed_trc[0] - this._zoomed_blc[0]) / (this._zoomed_x_range[1] - this._zoomed_x_range[0])),
                    // @ts-ignore
                                   this._zoomed_blc[1] + Math.min(yr.start,yr.end) * ((this._zoomed_trc[1] - this._zoomed_blc[1]) / (this._zoomed_y_range[1] - this._zoomed_y_range[0])) ]
                    // @ts-ignore
                    let newtrc01 = [ this._zoomed_trc[0] + Math.max(xr.start,xr.end) * ((this._zoomed_trc[0] - this._zoomed_trc[0]) / (this._zoomed_x_range[1] - this._zoomed_x_range[0])),
                    // @ts-ignore
                                   this._zoomed_trc[1] + Math.max(yr.start,yr.end) * ((this._zoomed_trc[1] - this._zoomed_trc[1]) / (this._zoomed_y_range[1] - this._zoomed_y_range[0])) ]
                    // @ts-ignore
                    let newblc02 = [ this._zoomed_blc[0] + Math.min(xr.start,xr.end) * ((this._zoomed_x_range[1] - this._zoomed_x_range[0]) / (this._zoomed_trc[0] - this._zoomed_blc[0])),
                    // @ts-ignore
                                     this._zoomed_blc[1] + Math.min(yr.start,yr.end) * ((this._zoomed_y_range[1] - this._zoomed_y_range[0]) / (this._zoomed_trc[1] - this._zoomed_blc[1]))  ]
                    // @ts-ignore
                    let newtrc02 = [ this._zoomed_trc[0] + Math.max(xr.start,xr.end) * ((this._zoomed_x_range[1] - this._zoomed_x_range[0]) / (this._zoomed_trc[0] - this._zoomed_blc[0])),
                    // @ts-ignore
                                   this._zoomed_trc[1] + Math.max(yr.start,yr.end) * ((this._zoomed_y_range[1] - this._zoomed_y_range[0]) / (this._zoomed_trc[1] - this._zoomed_blc[1])) ]
                    console.log('NEW BLC 01', newblc01)
                    console.log('NEW TRC 01', newtrc01)
                    console.log('NEW BLC 02', newblc02)
                    console.log('NEW TRC 02', newtrc02)

                    // @ts-ignore
                    this._zoomed_blc = newblc01
                    // @ts-ignore
                    this._zoomed_trc = newtrc01
                    // @ts-ignore
	                //this.model.trigger_event( new DownsampleZoomEvent( newblc01, newtrc01 ) )
                    console.groupEnd( )
                }
            }
        }
    } */
}

export namespace DownsampleBoxZoomTool {
    export type Attrs = AttrsOf<Props>

    export type Props = BoxZoomTool.Props & {
        //downsample_state: Property<DownsampleState>
    }
}

export interface DownsampleBoxZoomTool extends DownsampleBoxZoomTool.Attrs {}

export class DownsampleBoxZoomTool extends BoxZoomTool {
    override properties: DownsampleBoxZoomTool.Props
    override __view_type__: DownsampleBoxZoomToolView

//    update: Signal<[[number,number],[number,number]],this>

    constructor(attrs?: Partial<DownsampleBoxZoomTool.Attrs>) {
        super(attrs)
    }

//    override initialize(): void {
//	super.initialize()
//	this.update = new Signal(this, "update")
//    }

    static {
        this.prototype.default_view = DownsampleBoxZoomToolView
        this.define<DownsampleBoxZoomTool.Props>(({ /*Any*/ }) => ({
            // downsample_state: [ Any ]
        }))

        //this.register_alias("box_zoom", () => new BoxZoomTool({dimensions: "both"}))
        //this.register_alias("xbox_zoom", () => new BoxZoomTool({dimensions: "width"}))
        //this.register_alias("ybox_zoom", () => new BoxZoomTool({dimensions: "height"}))
    }

    override tool_name: "Downsample Box Zoom"
}
