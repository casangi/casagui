import {remove_at} from "@bokehjs/core/util/array"
import {div, show, hide, empty} from "@bokehjs/core/dom"
import {Tabs, TabsView} from "@bokehjs/models/layouts/tabs"
import {input} from "@bokehjs/core/dom"
import * as p from "@bokehjs/core/properties"
//import tabs_css, * as tabs from "@bokehjs/styles/tabs.css"
import * as tabs from "@bokehjs/styles/tabs.css"

export class CollapsibleTabsView extends TabsView {
    declare model: CollapsibleTabs

    checkbox_el: HTMLInputElement

    override connect_signals( ): void {
        super.connect_signals( )
    }

    override render(): void {
        const {hidden} = this.model.properties
        this.on_change( hidden, ( ) => {
            if ( hidden.get_value( ) && this.layout ) {
                //this.layout.set_sizing({height: 10, height_policy: "fixed"})
                this.model.max_height = 100
                this.layout.dirty = true
            }
            console.log( '----------->>>hidden>>>change>>>>>>>>', this.layout ? this.layout : {} )
            this._update_headers( )
            this.update_children( )
        })
        this.checkbox_el = input({type: "checkbox", checked: !hidden.get_value( )})
        this.checkbox_el.addEventListener("change", () => {
            this.model.hidden = !this.checkbox_el.checked
            console.log(`>>>>>>>>>checkbox>>change>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> ${this.model.hidden}`)
        })
        /*** super.render( ) will invoke _update_headers( ) below which uses this.checkbox_el ... ***/
        super.render( )
    }

    protected override _update_headers(): void {
        const {active,hidden} = this.model.properties
        console.log(`>>>>>>>>>update>>headers>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> ${hidden.get_value( )}`)
        const headers = this.model.tabs.map((tab, i) => {
            const el = div({class: [tabs.tab, i == active.get_value( ) ? tabs.active : null], tabIndex: 0}, tab.title)
            el.addEventListener("click", (event) => {
                if (this.model.disabled)
                    return
                if (event.target == event.currentTarget)
                    super.change_active(i)
                })
                if (tab.closable) {
                    const close_el = div({class: tabs.close})
                    close_el.addEventListener("click", (event) => {
                        if (event.target == event.currentTarget) {
                            this.model.tabs = remove_at(this.model.tabs, i)

                            const ntabs = this.model.tabs.length
                            if (this.model.active > ntabs - 1)
                                this.model.active = ntabs - 1
                        }
                })
                el.appendChild(close_el)
            }
            if (this.model.disabled || tab.disabled) {
                el.classList.add(tabs.disabled)
            }
            return el
        })

        this.header_els = headers
        empty(this.header_el)
        this.header_el.append(this.checkbox_el, ...headers)
    }

    override update_active(): void {
        const {hidden} = this.model.properties
        const {child_views} = this
        console.log('>>>>>>>>>update>>active>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> SHOWING')
        const i = this.model.active

        const {header_els} = this
        for (const el of header_els) {
            el.classList.remove(tabs.active)
        }

        if (i in header_els) {
            header_els[i].classList.add(tabs.active)
        }

        for (const child_view of child_views) {
            hide(child_view.el)
        }

        if ( ! hidden.get_value( ) && i in child_views ) {
            show(child_views[i].el)
        }
    }

    override update_layout(): void {
        console.log( "!!!!!!!!!!!!!!!!>>>>>>>", this )
        console.log( "                >>>>>>>", this.layout )
        const {hidden} = this.model.properties
        if ( hidden.get_value( ) ) {
            //const layout = new FixedLayout( )
            //layout.set_sizing({width_policy: "fit", height_policy: "min"})
            //delete this.layout
            //this.layout = layout
            //if ( this.layout ) this.layout.set_sizing({height: 10, height_policy: "fixed"})
            //super.update_layout( )
            //this.set_sizing({width_policy: "fit", height_policy: "min"})
        }
        super.update_layout( )
    }
    override _update_layout(): void {
        console.log( "################>>>>>>>", this )
        console.log( "                >>>>>>>", this.layout )
        super._update_layout()
    }

    override _after_layout(): void {
        super._after_layout()
        const {hidden} = this.model.properties
        const {child_views} = this
        const {active} = this.model
        if ( hidden.get_value( ) && active in child_views) {
            const tab = child_views[active]
            hide(tab.el)
        }
/********************
    const {child_views} = this
    for (const child_view of child_views)
      hide(child_view.el)

    const {active} = this.model
    if (active in child_views) {
      const tab = child_views[active]
      show(tab.el)
    }
********************/
    }
}

export namespace CollapsibleTabs {
    export type Attrs = p.AttrsOf<Props>
    export type Props = Tabs.Props & {
        hidden: p.Property<boolean>
    }
}

export interface CollapsibleTabs extends CollapsibleTabs.Attrs {}

export class CollapsibleTabs extends Tabs {
    declare properties: CollapsibleTabs.Props
    declare __view_type__: CollapsibleTabsView

    static __module__ = "casagui.bokeh.models._collapsible_tabs"

    constructor(attrs?: Partial<CollapsibleTabs.Attrs>) {
        super(attrs)
    }

    static {
        this.prototype.default_view = CollapsibleTabsView
        this.define<CollapsibleTabs.Props>(({Boolean}) => ({
            hidden: [ Boolean, false ],
        }))
    }
}
