'''
Functions to create a raster xarray Dataset from xradio ProcessingSet after applying plot inputs
'''

import numpy as np

from xradio.measurement_set._utils._utils.stokes_types import stokes_types

from casagui.data.measurement_set.processing_set._ps_concat import concat_ps_xds
from casagui.data.measurement_set.processing_set._ps_coords import set_datetime_coordinate
from casagui.data.measurement_set.processing_set._ps_select import select_ps
from casagui.data.measurement_set.processing_set._xds_data import get_axis_data

AGGREGATOR_OPTIONS = ['max', 'mean', 'median', 'min', 'std', 'sum', 'var']

def raster_data(ps, plot_inputs, logger):
    '''
    Create raster xds: y_axis vs x_axis for vis axis.
        ps (xradio ProcessingSet): input MSv4 datasets.
        plot_inputs (dict): user-selected values for plot
        logger (graphviper logger): logger
    Returns: selected xarray Dataset of visibility component and updated selection
    '''
    raster_ps, updated_selection = _select_raster_ps(ps, plot_inputs, logger)
    plot_inputs['selection'] = updated_selection

    # Create xds from concat ms_xds in ps
    raster_xds = concat_ps_xds(raster_ps, logger)
    correlated_data = plot_inputs['correlated_data']
    if raster_xds[correlated_data].count() == 0:
        raise RuntimeError("Plot failed: raster plane selection yielded data with all nan values.")

    # Set complex component of vis data
    raster_xds[correlated_data] = get_axis_data(raster_xds,
        plot_inputs['vis_axis'],
        plot_inputs['selection']['data_group']
    )

    # Convert float time to datetime
    set_datetime_coordinate(raster_xds)

    if plot_inputs['aggregator'] and plot_inputs['agg_axis']:
        raster_xds = aggregate_data(raster_xds, plot_inputs, logger)

    logger.debug(f"Plotting visibility data with shape: {raster_xds[correlated_data].shape}")
    return raster_xds

def _select_raster_ps(ps, plot_inputs, logger):
    ''' Select default dimensions if needed for raster data '''
    # Determine which dims must be selected, add to selection, and do selection
    dims_to_select = _get_raster_selection_dims(plot_inputs)
    input_selection = plot_inputs['selection']

    if dims_to_select:
        dim_selection = {}
        for dim in dims_to_select:
            # Select first value (by index) and add to input selection, or apply iter_axis value
            # (user selection would have been applied previously)
            if dim not in input_selection:
                input_selection[dim] = _get_first_dim_value(ps, dim)
                dim_selection[dim] = input_selection[dim]
            elif plot_inputs['iter_axis']:
                dim_selection[dim] = input_selection[dim]
        if dim_selection:
            logger.info(f"Applying default raster plane selection (using first index or iter value): {dim_selection}")
            return select_ps(ps, dim_selection, logger), input_selection
    return ps, input_selection

def _get_raster_selection_dims(plot_inputs):
    ''' Return which dimensions should be selected for raster plot.
        List of dimensions which are not x, y, or agg axis. '''
    data_dims = plot_inputs['data_dims'].copy()
    if plot_inputs['x_axis'] in data_dims:
        data_dims.remove(plot_inputs['x_axis'])
    if plot_inputs['y_axis'] in data_dims:
        data_dims.remove(plot_inputs['y_axis'])
    if plot_inputs['agg_axis']:
        for axis in plot_inputs['agg_axis']:
            data_dims.remove(axis)
    return data_dims

def _get_first_dim_value(ps, dim):
    ''' Return value of first dimension by index for polarization or by value for others. '''
    if dim == "polarization":
        # Get sorted list of polarization ids used
        pol_names = list(stokes_types.values())
        id_list = []
        for key in ps:
            for pol in ps[key].polarization.values:
                id_list.append(pol_names.index(pol))
        sorted_pol_id = sorted(list(set(id_list)))
        first_id = sorted_pol_id[0]
        return pol_names[first_id]

    # Get sorted values list
    values = []
    for xds in ps.values():
        values.extend(xds[dim].values.tolist())
    values = sorted(list(set(values)))
    return values[0]

def _add_index_dimensions(xds):
    ''' Add index coordinates for plotting if coord has dimension '''
    # Baseline/antenna id
    if "baseline" in xds.coords and xds.baseline.dims:
        xds = xds.assign_coords({"baseline_id": (xds.baseline.dims, np.array(range(xds.baseline.size)))})
        xds = xds.swap_dims({"baseline": "baseline_id"})
    elif "antenna_name" in xds.coords and xds.antenna_name.dims:
        xds = xds.assign_coords({"antenna_id": (xds.antenna_name.dims, np.array(range(xds.antenna_name.size)))})

    # Polarization id
    if "polarization" in xds.coords and xds.polarization.dims:
        xds = xds.assign_coords({"polarization_id": (xds.polarization.dims, np.array(range(xds.polarization.size)))})

    return xds

def aggregate_data(xds, plot_inputs, logger):
    ''' Apply aggregator to agg axis list. '''
    aggregator = plot_inputs['aggregator']
    agg_axis = plot_inputs['agg_axis']
    logger.debug(f"Applying {aggregator} to {agg_axis}.")
    agg_xds = xds

    if aggregator == 'max':
        agg_xds = xds.max(dim=agg_axis, keep_attrs=True)
    elif aggregator == 'mean':
        agg_xds = xds.mean(dim=agg_axis, keep_attrs=True)
    elif aggregator == 'median':
        agg_xds = xds.median(dim=agg_axis, keep_attrs=True)
    elif aggregator == 'min':
        agg_xds = xds.min(dim=agg_axis, keep_attrs=True)
    elif aggregator == 'std':
        agg_xds = xds.std(dim=agg_axis, keep_attrs=True)
    elif aggregator == 'sum':
        agg_xds = xds.sum(dim=agg_axis, keep_attrs=True)
    elif aggregator == 'var':
        agg_xds = xds.var(dim=agg_axis, keep_attrs=True)
    return agg_xds
