import {ButtonGroup, ButtonGroupView} from "models/widgets/button_group"

//import {classes} from "core/dom"
import * as p from "core/properties"

//import * as buttons from "models/widgets/styles/buttons.css"

export class ICleanButtonGroupView extends ButtonGroupView {
  model: ICleanButtonGroup

  change_active(i: number): void {
    if (this.model.active !== i) {
      this.model.active = i
    }
  }

  protected _update_active(): void {
    //const {active} = this.model

     //this._buttons.forEach((button, i) => {
       //classes(button).toggle(buttons.active, active === i)
     //})
  }
}

export namespace ICleanButtonGroup {
  export type Attrs = p.AttrsOf<Props>

  export type Props = ButtonGroup.Props & {
    active: p.Property<number | null>
  }
}

export interface ICleanButtonGroup extends ICleanButtonGroup.Attrs {}

export class ICleanButtonGroup extends ButtonGroup {
  properties: ICleanButtonGroup.Props
  __view_type__: ICleanButtonGroupView

  constructor(attrs?: Partial<ICleanButtonGroup.Attrs>) {
    super(attrs)
  }

  static init_ICleanButtonGroup(): void {
    this.prototype.default_view = ICleanButtonGroupView

    this.define<ICleanButtonGroup.Props>(({Int, Nullable}) => ({
      active: [ Nullable(Int), null ],
    }))
  }
}