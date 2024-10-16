import {ResetTool, ResetToolView} from "@bokehjs/models/tools/actions/reset_tool"
import * as p from "@bokehjs/core/properties"
import {tool_icon_reset} from "@bokehjs/styles/icons.css"
import { CallbackLike0 } from "@bokehjs/core/util/callbacks";
import {execute} from "@bokehjs/core/util/callbacks"

export class CBResetToolView extends ResetToolView {
  declare model: CBResetTool

  override doit(): void {
    // reset() issues the RangesUpdate event
    const {precallback,postcallback} = this.model
    if ( precallback != null ) void execute( precallback, this.model )
    this.plot_view.reset()
    if ( postcallback != null ) void execute( postcallback,  this.model )
  }
}

export namespace CBResetTool {
  export type Attrs = p.AttrsOf<Props>

    export type Props = ResetTool.Props & {
        precallback: p.Property<CallbackLike0<CBResetTool> | null>;
        postcallback: p.Property<CallbackLike0<CBResetTool> | null>;
    }
}

export interface CBResetTool extends CBResetTool.Attrs {}

export class CBResetTool extends ResetTool {
  declare properties: CBResetTool.Props
  declare __view_type__: CBResetToolView

  static __module__ = "casagui.bokeh.tools._cbreset_tool"

  constructor(attrs?: Partial<CBResetTool.Attrs>) {
    super(attrs)
  }

  static {
    this.prototype.default_view = CBResetToolView
    this.define<CBResetTool.Props>(({Any, Nullable}) => ({
      precallback: [ Nullable(Any), null ],
      postcallback: [ Nullable(Any), null ],
    }))

    this.register_alias("cbreset", () => new CBResetTool())
  }

  override tool_name = "CBReset"
  override tool_icon = tool_icon_reset
}
