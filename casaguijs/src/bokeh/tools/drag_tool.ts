import * as p from "@bokehjs/core/properties"
import {GestureTool, GestureToolView} from "@bokehjs/models/tools/gestures/gesture_tool"
import {PanEvent} from "@bokehjs/core/ui_events"
import {Drag,DragStart,DragEnd,DragState} from "../events"
import {px_from_sx,py_from_sy,dx_from_px,dy_from_py} from "../util/find"
import { CallbackLike1 } from "@bokehjs/models/callbacks/callback";

export class DragToolView extends GestureToolView {
  declare model: DragTool

  override _pan_start(ev: PanEvent): void {
    this.model.document?.interactive_start(this.plot_view.model)
    const sx = px_from_sx(this.plot_view,ev.sx)
    const sy = py_from_sy(this.plot_view,ev.sy)
    const x = dx_from_px(this.plot_view,sx)
    const y = dy_from_py(this.plot_view,sy)
    const {start} = this.model
    if ( start ) {
      start.execute( this.model, { sx, sy, x, y,
                                   delta_x: ev.dx,
                                   delta_y: -ev.dy,
                                   shift: ev.modifiers.shift,
                                   ctrl: ev.modifiers.ctrl,
                                   alt: ev.modifiers.alt } )
    } else {
      this.model.trigger_event( new DragStart( sx,sy,x,y,ev.dx,-ev.dy,
                                               ev.modifiers ) )
    }
  }

  override _pan(ev: PanEvent): void {
    this.model.document?.interactive_start(this.plot_view.model)
    const sx = px_from_sx(this.plot_view,ev.sx)
    const sy = py_from_sy(this.plot_view,ev.sy)
    const x = dx_from_px(this.plot_view,sx)
    const y = dy_from_py(this.plot_view,sy)
    const {move} = this.model
    if ( move ) {
      move.execute( this.model, { sx, sy, x, y,
                                  delta_x: ev.dx,
                                  delta_y: -ev.dy,
                                  shift: ev.modifiers.shift,
                                  ctrl: ev.modifiers.ctrl,
                                  alt: ev.modifiers.alt } )
    } else {
      this.model.trigger_event( new Drag( sx,sy,x,y,ev.dx,-ev.dy,
                                          ev.modifiers ) )
    }
  }

  override _pan_end(ev: PanEvent): void {
    const sx = px_from_sx(this.plot_view,ev.sx)
    const sy = py_from_sy(this.plot_view,ev.sy)
    const x = dx_from_px(this.plot_view,sx)
    const y = dy_from_py(this.plot_view,sy)
    const {end} = this.model
    if ( end ) {
      end.execute( this.model, { sx, sy, x, y,
                                 delta_x: ev.dx,
                                 delta_y: -ev.dy,
                                 shift: ev.modifiers.shift,
                                 ctrl: ev.modifiers.ctrl,
                                 alt: ev.modifiers.alt } )
    } else {
      this.model.trigger_event( new DragEnd( sx,sy,x,y,ev.dx,-ev.dy,
                                             ev.modifiers ) )
    }
  }

}

export namespace DragTool {
  export type Attrs = p.AttrsOf<Props>

  export type Props = GestureTool.Props & {
      start: p.Property<CallbackLike1<DragTool,DragState> | null>;
      move: p.Property<CallbackLike1<DragTool,DragState> | null>;
      end: p.Property<CallbackLike1<DragTool,DragState> | null>;
  }
}

export interface DragTool extends DragTool.Attrs {}

export class DragTool extends GestureTool {
  declare properties: DragTool.Props
  declare __view_type__: DragToolView

  static __module__ = "casagui.bokeh.tools._drag_tool"

  constructor(attrs?: Partial<DragTool.Attrs>) {
    super(attrs)
  }

  static {
      this.prototype.default_view = DragToolView
      this.define<DragTool.Props>(({Any, Nullable}) => ({
          start: [ Nullable(Any), null ],
          move: [ Nullable(Any), null ],
          end: [ Nullable(Any), null ],
      }))
  }

  override tool_name = "Drag"
  override event_type = "pan" as "pan"
  override default_order = 10

}
