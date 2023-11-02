import {UIElement, UIElementView} from "@bokehjs/models/ui/ui_element"
import {logger} from "@bokehjs/core/logging"
import {Signal} from "@bokehjs/core/signaling"
import {CSSOurStyles} from "@bokehjs/core/dom"
import {isNotNull} from "@bokehjs/core/util/types"
import * as p from "@bokehjs/core/properties"

import {build_view, build_views, ViewStorage, IterViews} from "@bokehjs/core/build_views"
import {DOMElementView} from "@bokehjs/core/dom_view"
import {Layoutable} from "@bokehjs/core/layout"
import {LayoutDOMView} from "@bokehjs/models/layouts/layout_dom"
import {defer} from "@bokehjs/core/util/defer"
import {CanvasLayer} from "@bokehjs/core/util/canvas"
import {SerializableState} from "@bokehjs/core/view"
import {Tooltip, TooltipView} from "@bokehjs/models/ui/tooltip"

export class TipView extends UIElementView {
  declare model: Tip
  declare parent: DOMElementView | null

  protected tooltip: TooltipView
  protected hover_wait: number

  protected readonly _child_views: ViewStorage<UIElement> = new Map()

  layout?: Layoutable

  readonly mouseenter = new Signal<MouseEvent, this>(this, "mouseenter")
  readonly mouseleave = new Signal<MouseEvent, this>(this, "mouseleave")

  get is_layout_root(): boolean {
    return this.is_root || !(this.parent instanceof LayoutDOMView)
  }

  private _resized = false

  override _after_resize(): void {
    this._resized = true
    super._after_resize()

    if (this.is_layout_root && !this._was_built) {
      // This can happen only in pathological cases primarily in tests.
      // ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- 
      //  Thu Nov  2 11:51:12 EDT 2023:
      //
      //  This error was happening probably due to using LayoutDOM as a model
      //  while still being a child of a LayoutDOM derived class.
      //
      //  Changing is_layout_root( ) back to:
      //
      //      this.is_root || !(this.parent instanceof LayoutDOMView)
      //                Instead of TipView ------------^^^^^^^^^^^^^
      //
      //  resolved the problem with this class, but this warning was still happening
      //  with the child rendering. Changing the loop in render( ) below from:
      //
      //      for (const child_view of this.child_views) {
      //          child_view.render()
      //          this.shadow_el.appendChild(child_view.el)
      //      }
      //
      //  to:
      //
      //      for (const child_view of this.child_views) {
      //          child_view.render_to(this.el)
      //          this.shadow_el.appendChild(child_view.el)
      //      }
      //
      //  resolved the worning message from the child.
      // ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----
      logger.warn(`${this} wasn't built properly`)
      this.render_to(null)
    } else
      this.compute_layout()
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
    for (const child_view of this.child_views)
      child_view.remove()
    this._child_views.clear()
    super.remove()
  }

  override connect_signals(): void {
    super.connect_signals()

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
    yield* this.child_views
    yield this.tooltip
  }

  get child_models(): UIElement[] {
    return [ this.model.child ]
  }

  get child_views(): UIElementView[] {
    // TODO In case of a race condition somewhere between layout, resize and children updates,
    // child_models and _child_views may be temporarily inconsistent, resulting in undefined
    // values. Eventually this shouldn't happen and undefined should be treated as a bug.
    return this.child_models.map((child) => this._child_views.get(child)).filter(isNotNull)
  }

  get layoutable_views(): TipView[] {
    return this.child_views.filter((c): c is TipView => c instanceof TipView)
  }

  async build_child_views(): Promise<UIElementView[]> {
    const {created, removed} = await build_views(this._child_views, this.child_models, {parent: this})

    for (const view of removed) {
      this._resize_observer.unobserve(view.el)
    }

    for (const view of created) {
      this._resize_observer.observe(view.el, {box: "border-box"})
    }

    return created
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

    for (const child_view of this.child_views) {
      child_view.render_to(this.el)
      this.shadow_el.appendChild(child_view.el)
      // No after_render() here. See r_after_render().
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
  }

  protected _update_layout(): void {
    const styles: CSSOurStyles = {}
    this.style.append(":host", styles)
  }

  update_layout(): void {
    this.update_style()

    for (const child_view of this.layoutable_views) {
      child_view.update_layout()
    }

    this._update_layout()
  }

  get is_managed(): boolean {
    return this.parent instanceof TipView
  }

  /**
   * Update CSS layout with computed values from canvas layout.
   * This can be done more frequently than `_update_layout()`.
   */
  protected _measure_layout(): void { }

  measure_layout(): void {
    for (const child_view of this.layoutable_views) {
      child_view.measure_layout()
    }

    this._measure_layout()
  }

  private _layout_computed: boolean = false

  compute_layout(): void {
    if (this.parent instanceof TipView) { // TODO: this.is_managed
      this.parent.compute_layout()
    } else {
      this.measure_layout()
      this.update_bbox()
      this._compute_layout()
      this.after_layout()
    }
    this._layout_computed = true
  }

  protected _compute_layout(): void {
    if (this.layout != null) {
      this.layout.compute(this.bbox.size)

      for (const child_view of this.layoutable_views) {
        if (child_view.layout == null)
          child_view._compute_layout()
        else
          child_view._propagate_layout()
      }
    } else {
      for (const child_view of this.layoutable_views) {
        child_view._compute_layout()
      }
    }
  }

  // not called in simple testing
  protected _propagate_layout(): void {
    for (const child_view of this.layoutable_views) {
      if (child_view.layout == null) {
        child_view._compute_layout()
      }
    }
  }

  override update_bbox(): boolean {
    for (const child_view of this.layoutable_views) {
      child_view.update_bbox()
    }

    const changed = super.update_bbox()

    if (this.layout != null) {
      this.layout.visible = this.is_displayed
    }

    return changed
  }

  protected _after_layout(): void {}

  after_layout(): void {
    for (const child_view of this.layoutable_views) {
      child_view.after_layout()
    }

    this._after_layout()
  }

  private _was_built: boolean = false
  override render_to(element: Node | null): void {
    if (!this.is_layout_root)
      throw new Error(`${this.toString()} is not a root layout`)

    this.render()
    if (element != null)
      element.appendChild(this.el)
    this.r_after_render()
    this._was_built = true

    this.notify_finished()
  }

  r_after_render(): void {
    for (const child_view of this.child_views) {
      if (child_view instanceof TipView)
        child_view.r_after_render()
      else
        child_view.after_render()
    }

    this.after_render()
  }

  override after_render(): void {
    if (!this.is_managed) {
      this.invalidate_layout()
    }

    if (!this._has_finished) {
      if (!this.is_displayed) {
        this.finish()
      } else {
        // In case after_resize() wasn't called (see regression test for issue
        // #9113), then wait one macro task and consider this view finished.
        defer().then(() => {
          if (!this._resized) {
            this.finish()
          }
        })
      }
    }
  }

  invalidate_layout(): void {
    // TODO: it would be better and more efficient to do a localized
    // update, but for now this guarantees consistent state of layout.
    if (this.parent instanceof TipView) {
      this.parent.invalidate_layout()
    } else {
      this.update_layout()
      this.compute_layout()
    }
  }

  override has_finished(): boolean {
    if (!super.has_finished()) {
      return false
    }

    if (this.is_layout_root && !this._layout_computed) {
      return false
    }

    for (const child_view of this.child_views) {
      if (!child_view.has_finished()) {
        return false
      }
    }

    return true
  }

  // not called in simple testing
  override export(type: "auto" | "png" | "svg" = "auto", hidpi: boolean = true): CanvasLayer {
    const output_backend = (() => {
      switch (type) {
        case "auto": // TODO: actually infer the best type
        case "png": return "canvas"
        case "svg": return "svg"
      }
    })()

    const composite = new CanvasLayer(output_backend, hidpi)

    const {x, y, width, height} = this.bbox
    composite.resize(width, height)

    const bg_color = getComputedStyle(this.el).backgroundColor
    composite.ctx.fillStyle = bg_color
    composite.ctx.fillRect(x, y, width, height)

    for (const view of this.child_views) {
      const region = view.export(type, hidpi)
      const {x, y} = view.bbox
      composite.ctx.drawImage(region.canvas, x, y)
    }

    return composite
  }

  // not called in simple testing
  override serializable_state(): SerializableState {
    return {
      ...super.serializable_state(),
      children: this.child_views.map((child) => child.serializable_state()),
    }
  }
}

export namespace Tip {
  export type Attrs = p.AttrsOf<Props>

  export type Props = UIElement.Props & {
    child: p.Property<UIElement>
    tooltip: p.Property<Tooltip>
    hover_wait: p.Property<number>
  }
}

export interface Tip extends Tip.Attrs {}

export class Tip extends UIElement {
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
