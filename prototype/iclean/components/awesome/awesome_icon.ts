import {AbstractIcon, AbstractIconView} from "models/widgets/abstract_icon"
import * as p from "core/properties"

import "./fontawesome.less"

export class AwesomeIconView extends AbstractIconView {
  model: AwesomeIcon

  connect_signals(): void {
    super.connect_signals()
    this.connect(this.model.change, () => this.render())
  }

  render(): void {
    super.render()

    this.el.style.display = "inline"
    this.el.style.verticalAlign = "middle"
    this.el.style.fontSize = `${this.model.size}em`

    this.el.classList.add("bk-u-fa")
    this.el.classList.add(`bk-u-fa-${this.model.icon_name}`)

    if (this.model.flip != null)
      this.el.classList.add(`bk-u-fa-flip-${this.model.flip}`)

    if (this.model.spin)
      this.el.classList.add("bk-u-fa-spin")
  }
}

export namespace AwesomeIcon {
  export type Attrs = p.AttrsOf<Props>

  export type Props = AbstractIcon.Props & {
    icon_name: p.Property<string>
    size: p.Property<number>
    flip: p.Property<"horizontal" | "vertical" | null>
    spin: p.Property<boolean>
  }
}

export interface AwesomeIcon extends AwesomeIcon.Attrs {}

export class AwesomeIcon extends AbstractIcon {
  properties: AwesomeIcon.Props
  __view_type__: AwesomeIconView

  constructor(attrs?: Partial<AwesomeIcon.Attrs>) {
    super(attrs)
  }

  static init_AwesomeIcon(): void {
    this.prototype.default_view = AwesomeIconView

    this.define<AwesomeIcon.Props>(({Boolean, String, Number, Enum, Nullable}) => ({
      icon_name: [ String, "check" ],
      size:      [ Number, 1 ],
      flip:      [ Nullable(Enum("horizontal", "vertical")) ],
      spin:      [ Boolean, false ],
    }))
  }
}
