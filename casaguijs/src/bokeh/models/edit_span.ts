import {Span,SpanView} from "@bokehjs/models/annotations/span"
import type {PanEvent} from "@bokehjs/core/ui_events"
import {LODStart,LODEnd} from "@bokehjs/core/bokeh_events"
import type * as p from "@bokehjs/core/properties"
//
// It is not clear that it is possible to create and register new events:
// ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---
//import {EditStart,EditEnd} from "../events"
// ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---  ---
// so instead we're using the LODStart and LODEnd because they have no
// properties and are PlotEvents
//
export class EditSpanView extends SpanView {
  declare model: EditSpan

  override on_pan_start(ev: PanEvent): boolean {
    const result = super.on_pan_start( ev )
    this.model.trigger_event( new LODStart( ) )
    return result
  }

  override on_pan(ev: PanEvent): void {
    super.on_pan( ev )
  }

  override on_pan_end(ev: PanEvent): void {
    super.on_pan_end( ev )
    this.model.trigger_event( new LODEnd( ) )
  }

}

export namespace EditSpan {
  export type Attrs = p.AttrsOf<Props>
  export type Props = Span.Props
}

export interface EditSpan extends EditSpan.Attrs {}

export class EditSpan extends Span {
  declare properties: EditSpan.Props
  declare __view_type__: EditSpanView
    
  // casagui.bokeh.models._edit_span.EditSpan
  static __module__ = "casagui.bokeh.models._edit_span"


  constructor(attrs?: Partial<EditSpan.Attrs>) {
    super(attrs)
  }

  static {
    this.prototype.default_view = EditSpanView
  }

}
