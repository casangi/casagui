import {PolyAnnotation,PolyAnnotationView} from "@bokehjs/models/annotations/poly_annotation"
//import {ButtonClick} from "core/bokeh_events"
// @ts-ignore:
//import type {PanEvent, Pannable, MoveEvent, Moveable, KeyModifiers} from "core/ui_events"
import type * as p from "@bokehjs/core/properties"
//import type {PanEvent, Pannable, MoveEvent, Moveable, KeyModifiers} from "core/ui_events"
import type {Moveable} from "@bokehjs/core/ui_events"
//import type {PanEvent, Pannable, MoveEvent, Moveable, KeyModifiers} from "core/ui_events"
import type {MoveEvent,PanEvent} from "@bokehjs/core/ui_events"
import {MouseEnter,MouseLeave,PanStart,PanEnd,RangesUpdate} from "@bokehjs/core/bokeh_events"

//import {MouseEnter/*,MouseLeave*/} from "@bokehjs/core/bokeh_events"

export class EvPolyAnnotationView extends PolyAnnotationView implements Moveable {
    declare model: EvPolyAnnotation

    override on_enter( event: MoveEvent ): boolean {
        const {x_scale, y_scale} = this.plot_view.frame  
        const mouse_ev = new MouseEnter( event.sx,
                                         event.sy,
                                         x_scale.invert(event.sx),
                                         y_scale.invert(event.sy),
                                         { shift: event.modifiers.shift,
                                           ctrl: event.modifiers.ctrl,
                                           alt: event.modifiers.alt } )
        const result = super.on_enter(event)
        this.model.trigger_event( mouse_ev )
        return result
    }

    override on_leave( event: MoveEvent ): void {
        const {x_scale, y_scale} = this.plot_view.frame  
        const mouse_ev = new MouseLeave( event.sx,
                                         event.sy,
                                         x_scale.invert(event.sx),
                                         y_scale.invert(event.sy),
                                         { shift: event.modifiers.shift,
                                           ctrl: event.modifiers.ctrl,
                                           alt: event.modifiers.alt } )
        void super.on_leave(event)
        this.model.trigger_event( mouse_ev )
    }

    override on_pan_start( event: PanEvent ): boolean {
        const {x_scale, y_scale} = this.plot_view.frame  
        const pan_ev = new PanStart( event.sx,
                                     event.sy,
                                     x_scale.invert(event.sx),
                                     y_scale.invert(event.sy),
                                     { shift: event.modifiers.shift,
                                       ctrl: event.modifiers.ctrl,
                                       alt: event.modifiers.alt } )
        const result = super.on_pan_start(event)
        this.model.trigger_event( pan_ev )
        return result
    }

    override on_pan_end( event: PanEvent ): void {
        const {x_scale, y_scale} = this.plot_view.frame  
        const pan_ev = new PanEnd( event.sx,
                                   event.sy,
                                   x_scale.invert(event.sx),
                                   y_scale.invert(event.sy),
                                   { shift: event.modifiers.shift,
                                     ctrl: event.modifiers.ctrl,
                                     alt: event.modifiers.alt } )
        void super.on_pan_end(event)
        this.model.trigger_event( pan_ev )
    }

    /******************************************************************************************************************
    Attempting to generate pan events (new Pan(...)) as the annotation is dragged breaks the panning behavior of super.
    ******************************************************************************************************************/
    override on_pan( event: PanEvent ): void {
        void super.on_pan(event)
        const ev = new RangesUpdate( event.sx, event.sx + event.dx,
                                     event.sy, event.sy + event.dy )
        this.model.trigger_event( ev )
    }

}

export namespace EvPolyAnnotation {
  export type Attrs = p.AttrsOf<Props>
  export type Props = PolyAnnotation.Props
}

export interface EvPolyAnnotation extends EvPolyAnnotation.Attrs {}

export class EvPolyAnnotation extends PolyAnnotation {
    declare properties: EvPolyAnnotation.Props
    declare __view_type__: EvPolyAnnotationView

    static __module__ =  "casagui.bokeh.annotations._ev_poly_annotation"

  constructor(attrs?: Partial<EvPolyAnnotation.Attrs>) {
    super(attrs)
  }

  static {
    this.prototype.default_view = EvPolyAnnotationView

    //this.override<PolyAnnotation.Props>({
    //    prefix: "Channel",
    //})
      
  }

}
