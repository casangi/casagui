import {AbstractButton, AbstractButtonView} from "@bokehjs/models/widgets/abstract_button"
import {Tooltip, TooltipView} from "@bokehjs/models/ui/tooltip"
import {BuiltinIcon} from "@bokehjs/models/ui/icons/builtin_icon"
import {build_view, IterViews} from "@bokehjs/core/build_views"
import {ButtonClick} from "@bokehjs/core/bokeh_events"
import {EventCallback} from "@bokehjs/model"
import * as p from "@bokehjs/core/properties"

import {dict} from "@bokehjs/core/util/object"

export class TipButtonView extends AbstractButtonView {
  declare model: TipButton

  protected tooltip: TooltipView
  protected hover_wait: number

  override click(): void {
    this.model.trigger_event(new ButtonClick())
    super.click()
  }

  override *children(): IterViews {
    yield* super.children()
    yield this.tooltip
  }

  override async lazy_initialize(): Promise<void> {
    await super.lazy_initialize()
    const {tooltip} = this.model
    this.tooltip = await build_view(tooltip, {parent: this})
  }

  override remove(): void {
    this.tooltip.remove()
    super.remove()
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
                        closable: persistent,
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
      if (!visible) {
        persistent = false
      }
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
    document.addEventListener("mousedown", (event) => {
      if ( typeof dict(this.model.js_event_callbacks).get(ButtonClick.prototype.event_name) == 'undefined' ) {
          // callback has not been set up with "js_on_click"
          const path = event.composedPath()
          if (path.includes(this.tooltip.el)) {
              return
          } else if (path.includes(this.el)) {
              persistent = !persistent
              toggle(persistent)
          } else {
              persistent = false
              toggle(false)
          }
      } else {
          // close any tooltip for invoking button click handler
          toggle(false)
          mouse_inside = false
      }
    })
    window.addEventListener("blur", () => {
      persistent = false
      toggle(false)
    })
  }
}

export namespace TipButton {
  export type Attrs = p.AttrsOf<Props>

  export type Props = AbstractButton.Props & {
    tooltip: p.Property<Tooltip>
    hover_wait: p.Property<number>
  }
}

export interface TipButton extends TipButton.Attrs {}

export class TipButton extends AbstractButton {
  declare properties: TipButton.Props
  declare __view_type__: TipButtonView

  static __module__ = "casagui.bokeh.models._tip_button"

  constructor(attrs?: Partial<TipButton.Attrs>) {
    super(attrs)
  }

  static {
    this.prototype.default_view = TipButtonView

    this.define<TipButton.Props>(({Ref,Number}) => ({
      tooltip: [ Ref(Tooltip) ],
      hover_wait: [ Number, 1.5 ]
    }))

    this.override<TipButton.Props>({
      label: "",
      icon: new BuiltinIcon({icon_name: "help", size: 18}),
      button_type: "default",
    })
  }

  on_click(callback: EventCallback<ButtonClick>): void {
    this.on_event(ButtonClick, callback)
  }

}
