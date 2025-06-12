'''
Check inputs to MsRaster plot() or its GUI
'''

from casagui.plot.ms_plot._ms_plot_constants import VIS_AXIS_OPTIONS, AGGREGATOR_OPTIONS

def check_inputs(inputs):
    ''' Check plot input types, and axis input values. '''
    _set_baseline_antenna_axis(inputs)
    _check_axis_inputs(inputs)
    _check_selection_input(inputs)
    _check_agg_inputs(inputs)
    _check_color_inputs(inputs)
    _check_other_inputs(inputs)

def _set_baseline_antenna_axis(inputs):
    ''' Set baseline axis to dimension in data_dims '''
    if 'data_dims' not in inputs:
        return

    data_dims = inputs['data_dims']
    baseline_dim = 'antenna_name' if 'antenna_name' in data_dims else 'baseline'

    # Convert baseline axis to existing baseline dimension
    baseline_dims = ['baseline', 'antenna_name']
    for axis in ['x_axis', 'y_axis', 'iter_axis', 'agg_axis']:
        if inputs[axis] in baseline_dims:
            inputs[axis] = baseline_dim

def _check_axis_inputs(inputs):
    ''' Check x_axis, y_axis, vis_axis, and iter_axis inputs. '''
    x_axis = inputs['x_axis']
    y_axis = inputs['y_axis']
    if x_axis == y_axis:
        raise ValueError(f"Invalid parameter values: x_axis {x_axis} cannot be same as y_axis {y_axis}.")

    iter_axis = inputs['iter_axis']
    if iter_axis and iter_axis in (x_axis, y_axis):
        raise ValueError(f"Invalid parameter value: iter_axis {iter_axis} cannot be x_axis ({x_axis}) or y_axis ({y_axis}).")

    data_dims = inputs['data_dims'] if 'data_dims' in inputs else None
    if data_dims:
        if x_axis not in data_dims or y_axis not in data_dims:
            raise ValueError(f"Invalid parameter value: x and y axis must be a data dimension in {data_dims}.")
        if iter_axis and iter_axis not in data_dims:
            raise ValueError(f"Invalid parameter value: iter_axis {iter_axis} must be a data dimension in {data_dims}.")

    vis_axis = inputs['vis_axis']
    if vis_axis not in VIS_AXIS_OPTIONS:
        raise ValueError(f"Invalid parameter value: vis_axis {vis_axis} must be one of {VIS_AXIS_OPTIONS}")

def _check_selection_input(inputs):
    ''' Check selection type and data_group selection.  Make copy of user selection. '''
    if 'selection' in inputs:
        user_selection = inputs['selection']
        if user_selection:
            if not isinstance(user_selection, dict):
                raise TypeError("Invalid parameter type: selection must be dictionary.")

def _check_agg_inputs(inputs):
    ''' Check aggregator and agg_axis. Set agg_axis if not set. '''
    aggregator = inputs['aggregator']
    agg_axis = inputs['agg_axis']

    x_axis = inputs['x_axis']
    y_axis = inputs['y_axis']
    data_dims = inputs['data_dims'] if 'data_dims' in inputs else None

    if aggregator and aggregator not in AGGREGATOR_OPTIONS:
        raise ValueError(f"Invalid parameter value: aggregator {aggregator} must be None or one of {AGGREGATOR_OPTIONS}.")

    if agg_axis:
        if not isinstance(agg_axis, str) and not isinstance(agg_axis, list):
            raise TypeError(f"Invalid parameter type: agg_axis {agg_axis} must be str or list.")

        # Make agg_axis a list
        if isinstance(agg_axis, str):
            agg_axis = [agg_axis]

        for axis in agg_axis:
            if axis in (x_axis, y_axis):
                raise ValueError(f"Invalid parameter value: agg_axis {agg_axis} cannot be x_axis ({x_axis}) or y_axis ({y_axis}).")
            if data_dims and axis not in data_dims:
                raise ValueError(f"Invalid parameter value: agg_axis {axis} must be a data dimension in {data_dims}.")
    elif aggregator and data_dims:
        # Set agg_axis to non-plotted dim axes
        agg_axis = data_dims.copy()
        agg_axis.remove(x_axis)
        agg_axis.remove(y_axis)
        if 'iter_axis' in inputs and inputs['iter_axis']:
            agg_axis.remove(inputs['iter_axis'])
    inputs['agg_axis'] = agg_axis

def _check_color_inputs(inputs):
    if inputs['color_mode']:
        color_mode = inputs['color_mode'].lower()
        valid_color_modes = ['auto', 'manual']
        if color_mode not  in valid_color_modes:
            raise ValueError(f"Invalid parameter value: color_mode {color_mode} must be None or one of {valid_color_modes}.")
        inputs['color_mode'] = color_mode

    if inputs['color_range']:
        if not (isinstance(inputs['color_range'], tuple) and len(inputs['color_range']) == 2):
            raise ValueError("Invalid parameter type: color_range must be None or a tuple of (min, max).")

def _check_other_inputs(inputs):
    if inputs['iter_range']:
        if not (isinstance(inputs['iter_range'], tuple) and len(inputs['iter_range']) == 2):
            raise ValueError("Invalid parameter type: iter_range must be None or a tuple of (start, end).")

    if inputs['subplots']:
        if not (isinstance(inputs['subplots'], tuple) and len(inputs['subplots']) == 2):
            raise ValueError("Invalid parameter type: subplots must be None or a tuple of (rows, columns).")

    if inputs['title'] and not isinstance(inputs['title'], str):
        raise TypeError("Invalid parameter type: title must be None or a string.")
