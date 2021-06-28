import { Slider, SliderView } from "models/widgets/slider"
import * as p from "core/properties"


/**
* Builds on Bokeh slider class to provide a websocket connected slider widget.
*
* @remarks
* This method is part of the {@link prototype/iclean/components/widgets/Slider | IClean}.
*
* @param socket - A tuple containing the websocket connection information: (address, port)
*
* @beta
*/

export class ICleanSliderView extends SliderView {
    model: ICleanSlider

    connect_signals(): void {
        super.connect_signals()
    }

    render(): void {
        console.log("render")
        console.log(this.model)
        super.render()
    }
}

export namespace ICleanSlider {
    export type Attrs = p.AttrsOf<Props>
    export type Props = Slider.Props & {
        socket: p.Property<[string, number]>,
    }
}

export interface ICleanSlider extends ICleanSlider.Attrs { }

export class ICleanSlider extends Slider {
    properties: ICleanSlider.Props

    constructor(attrs?: Partial<ICleanSlider.Attrs>) {
        super(attrs)
    }

    static init_ICleanSlider(): void {
        this.prototype.default_view = ICleanSliderView;

        this.define<ICleanSlider.Props>( ({String, Number, Tuple}) => ({
            socket: [ Tuple(String, Number) ],
        }))
    }
}