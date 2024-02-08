import {LayoutDOM, LayoutDOMView} from "@bokehjs/models/layouts/layout_dom"
import {UIElement} from "@bokehjs/models/ui/ui_element"
import type {StyleSheetLike} from "@bokehjs/core/dom"
import {Tooltip, TooltipView} from "@bokehjs/models/ui/tooltip"
import {fieldset} from "@bokehjs/core/dom"
import type * as p from "@bokehjs/core/properties"

import {build_view, IterViews} from "@bokehjs/core/build_views"

export class TipView extends LayoutDOMView {
  declare model: Tip

  protected tooltip: TooltipView
  protected hover_wait: number
  fieldset_el: HTMLFieldSetElement

  override stylesheets(): StyleSheetLike[] {
      return [...super.stylesheets(), "*, *:before, *:after { box-sizing: border-box;  } fieldset { border: 0px; margin: 0px; padding: 0px; }"]
  }

  override async lazy_initialize(): Promise<void> {
    await super.lazy_initialize()
    await this.build_child_views()
    const {tooltip} = this.model
    this.tooltip = await build_view(tooltip, {parent: this})
  }

  // not called in simple testing
  override remove(): void {
    this.tooltip.remove()
    super.remove()
  }

  override connect_signals(): void {
    super.connect_signals()
    const {child} = this.model.properties
    this.on_change(child, () => this.update_children())

    this.el.addEventListener("mouseenter", (event) => {
      this.mouseenter.emit(event)
    })

    this.el.addEventListener("mouseleave", (event) => {
      this.mouseleave.emit(event)
    })
  }

  // not called in simple testing
  override *children(): IterViews {
    yield* super.children()
    yield this.tooltip
  }

  get child_models(): UIElement[] {
    return [this.model.child]
  }

  override render(): void {
    super.render()

    let wait_function_set = false
    let mouse_inside = false
    let persistent = false

    const toggle = (visible: boolean) => {
        if ( visible && ! wait_function_set ) {
            // display tooltip after hover_wait seconds if mouse is still inside button
            const {hover_wait} = this.model
            wait_function_set = true
            setTimeout( ( ) => {
                // setting `wait_function_set = false` here resulted in the wait function
                // being triggered again while the tooltip was still deployed
                if ( mouse_inside ) {
                    this.tooltip.model.setv( {
                        visible,
                        closable: false,
                    } )
                }
            }, hover_wait * 1000 )
        } else {
            wait_function_set = false
            this.tooltip.model.setv( {
                visible,
                closable: persistent,
            } )
        }
        //icon_el.style.visibility = visible && persistent ? "visible" : ""
    }

    this.on_change(this.tooltip.model.properties.visible, () => {
      const {visible} = this.tooltip.model
      toggle(visible)
    })

    this.el.addEventListener("mouseenter", () => {
      mouse_inside = true
      toggle(true)
    })

    this.el.addEventListener("mouseleave", () => {
      //js_event_callbacks.get(event_name, []))
      mouse_inside = false
      if (!persistent)
        toggle(false)
    })

    window.addEventListener("blur", () => {
      persistent = false
      toggle(false)
    })

    this.el.addEventListener("click", ( /*event*/ ) => {
      toggle(false)
    })

    const child_els = this.child_views.map((child) => child.el)
    this.fieldset_el = fieldset({}, ...child_els)
    this.shadow_el.appendChild(this.fieldset_el)
  }

  protected override _update_children(): void {
    const child_els = this.child_views.map((child) => child.el)
    this.fieldset_el.append(...child_els)
  }
}

export namespace Tip {
  export type Attrs = p.AttrsOf<Props>

  export type Props = LayoutDOM.Props & {
    child: p.Property<UIElement>
    tooltip: p.Property<Tooltip>
    hover_wait: p.Property<number>
  }
}

export interface Tip extends Tip.Attrs {}

export class Tip extends LayoutDOM {
  declare properties: Tip.Props
  declare __view_type__: TipView

  static __module__ = "casagui.bokeh.models._tip"

  constructor(attrs?: Partial<Tip.Attrs>) {
    super(attrs)
  }

  static {
    this.prototype.default_view = TipView

    this.define<Tip.Props>(({Ref,Number}) => ({
      child: [ Ref(UIElement) ],
      tooltip: [ Ref(Tooltip) ],
      hover_wait: [ Number, 1.5 ]
    }))
  }
}
