import {TextInput,TextInputView} from "@bokehjs/models/widgets/text_input"
// @ts-ignore:
import {StyleSheetLike,InlineStyleSheet} from "@bokehjs/core/dom"
import type * as p from "@bokehjs/core/properties"
import {MouseEnter,MouseLeave} from "@bokehjs/core/bokeh_events"

export class EvTextInputView extends TextInputView {
    declare model: EvTextInput

    override stylesheets(): StyleSheetLike[] {
        return [ ...super.stylesheets(),// ]
                 //new InlineStyleSheet( ".bk-input { border: 0px solid #ccc; padding: 0 var(--padding-vertical); border-bottom: 2px solid #ccc; }" ) ]
                 // new InlineStyleSheet( ".bk-input { border: 1px solid #ccc; padding: 0 var(--padding-vertical); padding: 0 var(--padding-horizontal); }" ) ]
                 new InlineStyleSheet( ".bk-input-prefix { padding: 0 var(--padding-vertical); }" ) ]
    }

    override connect_signals(): void {
        super.connect_signals()

        this.el.addEventListener("mouseenter", (event) => {
            this.model.trigger_event( new MouseEnter( event.screenX,
                                                      event.screenY,
                                                      event.x,
                                                      event.y,
                                                      { shift: event.shiftKey,
                                                        ctrl: event.ctrlKey,
                                                        alt: event.altKey } ) )
        })

        this.el.addEventListener("mouseleave", (event) => {
            this.model.trigger_event( new MouseLeave( event.screenX,
                                                      event.screenY,
                                                      event.x,
                                                      event.y,
                                                      { shift: event.shiftKey,
                                                        ctrl: event.ctrlKey,
                                                        alt: event.altKey } ) )
        })
  }


    override render(): void {
        super.render()
    }
}

export namespace EvTextInput {
  export type Attrs = p.AttrsOf<Props>
  export type Props = TextInput.Props
}

export interface EvTextInput extends EvTextInput.Attrs {}

export class EvTextInput extends TextInput {
    declare properties: EvTextInput.Props
    declare __view_type__: EvTextInputView

    static __module__ =  "casagui.bokeh.models._ev_text_input"

  constructor(attrs?: Partial<EvTextInput.Attrs>) {
    super(attrs)
  }

  static {
    this.prototype.default_view = EvTextInputView

    //this.override<TextInput.Props>({
    //    prefix: "Channel",
    //})
      
  }

}
