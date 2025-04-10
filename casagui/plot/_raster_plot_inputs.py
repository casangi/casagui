'''
Check inputs to MsRaster plot() or its GUI
'''

from casagui.data.measurement_set.processing_set._xds_data import VIS_AXIS_OPTIONS
from casagui.data.measurement_set.processing_set._ps_raster_data import AGGREGATOR_OPTIONS

def check_inputs(inputs):
    ''' Check plot input types, and axis input values. '''
    _set_baseline_antenna_axis(inputs)
    _check_axis_inputs(inputs)
    _check_selection_input(inputs)
    _check_agg_input(inputs)
    _check_title_input(inputs)
    inputs['have_inputs'] = True

def _set_baseline_antenna_axis(inputs):
    ''' Set baseline axis to dimension in data_dims '''
    data_dims = inputs['data_dims']
    baseline_dims = ['baseline', 'antenna_name']
    for dim in data_dims:
        if dim in baseline_dims:
            baseline_dim = dim
            break

    for axis in ['x_axis', 'y_axis', 'iter_axis', 'agg_axis']:
        if inputs[axis] in baseline_dims:
            inputs[axis] = baseline_dim

def _check_axis_inputs(inputs):
    ''' Check x_axis, y_axis, vis_axis, and iter_axis inputs. '''
    x_axis = inputs['x_axis']
    y_axis = inputs['y_axis']
    data_dims = inputs['data_dims']

    if x_axis not in data_dims or y_axis not in data_dims:
        raise ValueError(f"Invalid parameter value: select x and y axis from {data_dims}.")
    inputs['x_axis'] = x_axis
    inputs['y_axis'] = y_axis

    if inputs['vis_axis'] not in VIS_AXIS_OPTIONS:
        raise ValueError(f"Invalid parameter value: vis_axis {inputs['vis_axis']}. Options include {VIS_AXIS_OPTIONS}")

    iter_axis = inputs['iter_axis']
    if iter_axis and (iter_axis not in data_dims or iter_axis in (x_axis, y_axis)):
        raise RuntimeError(f"Invalid parameter value: iteration axis {iter_axis}. Must be dimension which is not a plot axis.")

def _check_selection_input(inputs):
    ''' Check selection type and data_group selection.  Make copy of user selection. '''
    if 'selection' in inputs:
        user_selection = inputs['selection']
        if user_selection:
            if not isinstance(user_selection, dict):
                raise RuntimeError("Invalid parameter type: selection must be dictionary.")

def _check_agg_input(inputs):
    ''' Check aggregator and agg_axis. Set agg_axis if not set. '''
    aggregator = inputs['aggregator']
    agg_axis = inputs['agg_axis']
    data_dims = inputs['data_dims']

    if aggregator and aggregator not in AGGREGATOR_OPTIONS:
        raise RuntimeError(f"Invalid parameter value: aggregator {aggregator}. Options include {AGGREGATOR_OPTIONS}.")

    if agg_axis:
        if not isinstance(agg_axis, str) and not isinstance(agg_axis, list):
            raise RuntimeError(f"Invalid parameter value: agg axis {agg_axis}. Options include one or more dimensions {data_dims}.")
        if isinstance(agg_axis, str):
            agg_axis = [agg_axis]
        for axis in agg_axis:
            if axis not in data_dims or axis in (inputs['x_axis'], inputs['y_axis']):
                raise RuntimeError(f"Invalid parameter value: aggregator axis {axis}. Must be dimension which is not a plot axis.")
    elif aggregator:
        # Set agg_axis to non-plotted dim axes
        agg_axis = data_dims.copy()
        agg_axis.remove(inputs['x_axis'])
        agg_axis.remove(inputs['y_axis'])
    inputs['agg_axis'] = agg_axis

def _check_title_input(inputs):
    if inputs['title'] and not isinstance(inputs['title'], str):
        raise RuntimeError("Invalid parameter type: title must be a string.")
