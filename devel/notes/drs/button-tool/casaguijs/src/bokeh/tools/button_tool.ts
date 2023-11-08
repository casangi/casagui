import {PlotActionTool, PlotActionToolView} from "@bokehjs/models/tools/actions/plot_action_tool"
import * as p from "@bokehjs/core/properties"
import {tool_icon_unknown} from "@bokehjs/styles/icons.css"

export class ButtonToolView extends PlotActionToolView {
  declare model: ButtonTool

  doit(): void {
    // reset() issues the RangesUpdate event
    console.log('>>>>>>>>------------------>> insert callback here')
  }
}

export namespace ButtonTool {
  export type Attrs = p.AttrsOf<Props>

  export type Props = PlotActionTool.Props
}

export interface ButtonTool extends ButtonTool.Attrs {}

export class ButtonTool extends PlotActionTool {
  declare properties: ButtonTool.Props
  declare __view_type__: ButtonToolView

  static __module__ = "casagui.bokeh.tools._button_tool"

  constructor(attrs?: Partial<ButtonTool.Attrs>) {
      super(attrs)
      console.log('>>>>>>>>>>',this.tool_icon)
  }

  static {
    this.prototype.default_view = ButtonToolView

    this.register_alias("reset", () => new ButtonTool())
  }

  override tool_name = "Callback"
  // default icon property supplied in python
  override tool_icon = tool_icon_unknown
}
