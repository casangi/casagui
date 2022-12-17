import {PanEvent} from "@bokehjs/core/ui_events"
import * as p from "@bokehjs/core/properties"
import {PanTool, PanToolView} from "@bokehjs/models/tools/gestures/pan_tool"

export class DownsamplePanToolView extends PanToolView {
    override model: DownsamplePanTool

    override _pan_end(e: PanEvent): void {
        console.group("DownsamplePan: _pan_end")
        console.log("Made it to _pan_end")
        console.log( e )
        console.log( this.plot_view.frame.bbox )
        super._pan_end(e)
        console.log("Called parent")
        console.groupEnd( )
    }
}

export namespace DownsamplePanTool {
    export type Attrs = p.AttrsOf<Props>

    export type Props = PanTool.Props & {
        //downsample_state: p.Property<DownsampleState>
    }
}

export interface DownsamplePanTool extends DownsamplePanTool.Attrs {}

export class DownsamplePanTool extends PanTool {
    override properties: DownsamplePanTool.Props
    override __view_type__: DownsamplePanToolView

    constructor(attrs?: Partial<DownsamplePanTool.Attrs>) {
        super(attrs)
    }

    static {
        this.prototype.default_view = DownsamplePanToolView
        this.define<DownsamplePanTool.Props>(({ /*Any*/ }) => ({
            // downsample_state: [ Any ]
        }))

        //this.register_alias("box_zoom", () => new BoxZoomTool({dimensions: "both"}))
        //this.register_alias("xbox_zoom", () => new BoxZoomTool({dimensions: "width"}))
        //this.register_alias("ybox_zoom", () => new BoxZoomTool({dimensions: "height"}))
    }

    override tool_name: "Downsample Pan"
}
