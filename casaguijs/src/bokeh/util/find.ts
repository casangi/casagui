import {CoordinateMapper} from "@bokehjs/core/util/bbox"
import {Scale} from "@bokehjs/models/scales/scale"
import {CoordinateUnits} from "@bokehjs/core/enums"
import {PlotView} from "@bokehjs/models/plots/plot"
// @ts-ignore: All imports in import declaration are unused.
import {Span, SpanView} from "@bokehjs/models/annotations/span"
import {View} from "@bokehjs/core/view"
import {Model} from "@bokehjs/model"

declare global {
    var Bokeh: {
        index: {
            [key: string]: View;
        }
    }
}

export function view( model: Model ): View | null {
    // find view for model using the global Bokeh index
    function find( view: View, id: string ): View | null {
        for (const v of view.children()) {
            if ( v.model.id === model.id ) {
                return v
            } else {
                if ( v.children( ) ) {
                    const result = find( v, id )
                    if ( result ) return result;
                }
            }
        }
        return null
    }
    return find( Bokeh.index[Object.keys(Bokeh.index)[0]], model.id )
}

export function span_coords( span: SpanView ) {
    // find span screen coordinates
    function compute( value: number | null, units: CoordinateUnits, scale: Scale, view: CoordinateMapper, canvas: CoordinateMapper ): number {
        if ( value != null )
            switch (units) {
                case "canvas": return canvas.compute(value)
                case "screen": return view.compute(value)
                case "data":   return scale.compute(value)
            }
        return NaN
    }
    const {frame, canvas} = span.plot_view
    const {x_scale, y_scale} = span.coordinates
    let height, sleft, stop, width, orientation = span.model.dimension
    if (span.model.dimension == "width") {
        stop = compute(span.model.location, span.model.location_units, y_scale, frame.bbox.yview, canvas.bbox.y_screen)
        sleft = frame.bbox.left
        width = frame.bbox.width
        height = span.model.line_width
    } else {
        stop = frame.bbox.top
        sleft = compute(span.model.location, span.model.location_units, x_scale, frame.bbox.xview, canvas.bbox.y_screen)
        width = span.model.line_width
        height = frame.bbox.height
    }
    return { stop, sleft, width, height, orientation }
}


//****************************************************************
//*** scalar coordinate functions                              ***
//****************************************************************
export function px_from_sx( view: PlotView, x: number ) {
    // map the screen x coordinates supplied as sx in cb_data for mouse
    // movement to the screen coordinate used within a plot
    return view.frame.bbox.x_view.invert(x)
}
export function py_from_sy( view: PlotView, y: number ) {
    // map the screen y coordinates supplied as sy in cb_data for mouse
    // movement to the screen coordinate used within a plot
    return view.frame.bbox.y_view.invert(y)
}

export function dx_from_px( view: PlotView, sx: number ) {
    // map the (plot) screen x coordinate supplied as sx in cb_data for mouse
    // movement to the data coordinate. sx is screen coordinates WITHIN the plot
    const fig_sx = view.frame.bbox.x_view.compute(sx)
    return view.frame.x_scale.invert(fig_sx)
}

export function dy_from_py( view: PlotView, sy: number ) {
    // map the (plot) screen y coordinate supplied as sy in cb_data for mouse
    // movement to the data coordinate. sy is screen coordinates WITHIN the plot
    const fig_sy = view.frame.bbox.y_view.compute(sy)
    return view.frame.y_scale.invert(fig_sy)
}

export function sx_from_dx( view: PlotView, dx: number ) {
    // map the data x coordinate supplied as x in cb_data for mouse
    // movement to the screen coordinate
    return view.frame.x_scale.compute(dx)
}

export function sy_from_dy( view: PlotView, dy: number ) {
    // map the data y coordinate supplied as y in cb_data for mouse
    // movement to the data coordinate used within the plot
    return view.frame.y_scale.compute(dy)
}

//****************************************************************
//*** vector coordinate functions                              ***
//****************************************************************
export function v_px_from_sx( view: PlotView, x: [ number ]) {
    // map the screen x coordinates supplied as sx in cb_data for mouse
    // movement to the screen coordinate used within a plot
    return view.frame.bbox.x_view.v_invert(x)
}
export function v_py_from_sy( view: PlotView, y: [ number ] ) {
    // map the screen y coordinates supplied as sy in cb_data for mouse
    // movement to the screen coordinate used within a plot
    return view.frame.bbox.y_view.v_invert(y)
}

export function v_dx_from_px( view: PlotView, sx: [ number ] ) {
    // map the (plot) screen x coordinate supplied as sx in cb_data for mouse
    // movement to the data coordinate
    const fig_sx = view.frame.bbox.x_view.v_compute(sx)
    return view.frame.x_scale.v_invert(fig_sx)
}

export function v_dy_from_py( view: PlotView, sy: [ number ] ) {
    // map the (plot) screen y coordinate supplied as sy in cb_data for mouse
    // movement to the data coordinate
    const fig_sy = view.frame.bbox.y_view.v_compute(sy)
    return view.frame.y_scale.v_invert(fig_sy)
}

export function v_sx_from_dx( view: PlotView, dx: [ number ] ) {
    // map the data x coordinate supplied as x in cb_data for mouse
    // movement to the screen coordinate
    return view.frame.x_scale.v_compute(dx)
}

export function v_sy_from_dy( view: PlotView, dy: [ number ] ) {
    // map the data y coordinate supplied as y in cb_data for mouse
    // movement to the data coordinate used within the plot
    return view.frame.y_scale.v_compute(dy)
}
