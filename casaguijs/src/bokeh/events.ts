import {Attrs} from "@bokehjs/core/types"
import {Pan,PanStart,PanEnd} from "@bokehjs/core/bokeh_events"
import {KeyModifiers} from "@bokehjs/core/ui_gestures"

export type DragState = {
    sx: number
    sy: number
    x: number
    y: number
    delta_x: number
    delta_y: number
} & KeyModifiers

export class Drag extends Pan { }

export class DragStart extends PanStart {
    constructor( sx: number, sy: number,
                 x: number, y: number,
                 readonly delta_x: number, readonly delta_y: number,
                 modifiers: KeyModifiers ) {
        super(sx, sy, x, y, modifiers )
    }

    protected override get event_values(): Attrs {
        const {delta_x, delta_y/*, direction*/} = this
        return {...super.event_values, delta_x, delta_y/*, direction*/}
    }
}

export class DragEnd extends PanEnd {
    constructor( sx: number, sy: number,
                 x: number, y: number,
                 readonly delta_x: number, readonly delta_y: number,
                 modifiers: KeyModifiers ) {
        super(sx, sy, x, y, modifiers)
    }

    protected override get event_values(): Attrs {
        const {delta_x, delta_y/*, direction*/} = this
        return {...super.event_values, delta_x, delta_y/*, direction*/}
    }
}
