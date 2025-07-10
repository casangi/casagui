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

  private isMouseInside: boolean = false;
  private debouncedShow: { (): void; cancel(): void };

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

  Show( ): void {
    this.tooltip.model.setv( {
      visible: true,
      closable: false,
    } )
  }

  unShow( ): void {
    this.tooltip.model.setv( {
      visible: false,
      closable: false,
    } )
  }

  override async lazy_initialize(): Promise<void> {
    const {hover_wait} = this.model
    this.debouncedShow = casalib.debounce( ( ) => {
        if (this.isMouseInside) this.Show( )
    }, hover_wait  * 1000 );

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

    this.el.addEventListener("mouseenter", () => {
      this.isMouseInside = true
      this.debouncedShow( )
    })
    this.el.addEventListener("mouseleave", () => {
      this.isMouseInside = false
      this.debouncedShow.cancel( )
      this.unShow( )
    })
    document.addEventListener("mousedown", (event) => {
      if ( typeof dict(this.model.js_event_callbacks).get(ButtonClick.prototype.event_name) == 'undefined' ) {
          // callback has not been set up with "js_on_click"
          const path = event.composedPath()
          if (path.includes(this.tooltip.el)) {
              return
          } else {
	      this.debouncedShow.cancel( )
	      this.unShow( )
          }
      } else {
          // close any tooltip for invoking button click handler
          this.isMouseInside = false
	  this.debouncedShow.cancel( )
	  this.unShow( )
      }
    })
    window.addEventListener("blur", () => {
      this.debouncedShow.cancel( )
      this.unShow( )
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
