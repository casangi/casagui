import {PanEvent} from "@bokehjs/core/ui_events"
import * as p from "@bokehjs/core/properties"
import {PanTool, PanToolView} from "@bokehjs/models/tools/gestures/pan_tool"
import { DownsampleState } from "../models/downsample_state"

export class ImagePanToolView extends PanToolView {
    override model: ImagePanTool

    override _pan_end(e: PanEvent): void {
    	console.group("ImagePan: _pan_end")
    	console.log("Made it to _pan_end")
        console.log( e )
        console.log( this.plot_view.frame.bbox )
        super._pan_end(e)
        console.log("Called parent")
        console.groupEnd( )
    }
}

export namespace ImagePanTool {
    export type Attrs = p.AttrsOf<Props>

    export type Props = PanTool.Props & {
        downsample_state: p.Property<DownsampleState>
    }
}

export interface ImagePanTool extends ImagePanTool.Attrs {}

export class ImagePanTool extends PanTool {
    override properties: ImagePanTool.Props
    override __view_type__: ImagePanToolView

    constructor(attrs?: Partial<ImagePanTool.Attrs>) {
        super(attrs)
    }

    static {
        this.prototype.default_view = ImagePanToolView
        this.define<ImagePanTool.Props>(({ Any }) => ({
            downsample_state: [ Any ]
        }))

        //this.register_alias("box_zoom", () => new BoxZoomTool({dimensions: "both"}))
        //this.register_alias("xbox_zoom", () => new BoxZoomTool({dimensions: "width"}))
        //this.register_alias("ybox_zoom", () => new BoxZoomTool({dimensions: "height"}))
    }

    override tool_name: "Image Pan"
}
