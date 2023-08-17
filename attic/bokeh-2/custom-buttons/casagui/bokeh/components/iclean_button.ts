import { Button, ButtonView } from "models/widgets/button"
import * as p from "core/properties"


/**
* Builds on Bokeh Button class to provide a websocket connected button widget.
*
* @remarks
* This method is part of the {@link prototype/iclean/components/widgets/Button | IClean}.
*
* @param socket - A tuple containing the websocket connection information: (address, port)
*
* @beta
*/

export class ICleanButtonView extends ButtonView {
    model: ICleanButton

    connect_signals(): void {
        super.connect_signals()
    }

    render(): void {
        console.log("render")
        console.log(this.model)
        super.render()
    }
}

export namespace ICleanButton {
    export type Attrs = p.AttrsOf<Props>
    export type Props = Button.Props & {
        socket: p.Property<[string, number]>,
    }
}

export interface ICleanButton extends ICleanButton.Attrs { }

export class ICleanButton extends Button {
    properties: ICleanButton.Props

    constructor(attrs?: Partial<ICleanButton.Attrs>) {
        super(attrs)
    }

    static init_ICleanButton(): void {
        this.prototype.default_view = ICleanButtonView;

        this.define<ICleanButton.Props>( ({String, Number, Tuple}) => ({
            socket: [ Tuple(String, Number) ],
        }))
    }
}