import {Model} from "@bokehjs/model"
import {View} from "@bokehjs/core/view"
import {AttrsOf, Property} from "@bokehjs/core/properties"

export class DownsampleStateView extends View {
    override model: DownsampleState
}

export namespace DownsampleState {
    export type Attrs = AttrsOf<Props>

    export type Props = Model.Props & {
        shape: Property<[number,number]>
        raw: Property<[number,number]>
        sampled: Property<[number,number]>
        viewport: Property<[[number,number],[number,number]]>
    }
}

export interface DownsampleState extends DownsampleState.Attrs {}

export class DownsampleState extends Model {
    override properties: DownsampleState.Props
    override __view_type__: DownsampleStateView

    constructor(attrs?: Partial<DownsampleState.Attrs>) {
        super(attrs)
    }

    static {
        this.prototype.default_view = DownsampleStateView
        this.define<DownsampleState.Props>(({ Tuple, Int }) => ({
            shape:    [Tuple(Int,Int), [-1,-1]],
            raw:      [Tuple(Int,Int), [-1,-1]],
            sampled:  [Tuple(Int,Int), [-1,-1]],
            viewport: [Tuple(Tuple(Int,Int),Tuple(Int,Int)), [[-1,-1],[-1,-1]]],
        }))
    }
}
