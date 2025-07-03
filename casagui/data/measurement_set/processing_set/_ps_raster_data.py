'''
Functions to create a raster xarray Dataset from xradio ProcessingSet after applying plot inputs
'''

import numpy as np

from xradio.measurement_set._utils._utils.stokes_types import stokes_types

from casagui.data.measurement_set.processing_set._ps_concat import concat_ps_xdt
from casagui.data.measurement_set.processing_set._ps_coords import set_datetime_coordinate
from casagui.data.measurement_set.processing_set._ps_select import select_ms
from casagui.data.measurement_set.processing_set._xds_data import get_correlated_data, get_axis_data

def raster_data(ps_xdt, plot_inputs, logger):
    '''
    Create raster xds: y_axis vs x_axis for vis axis.
        ps_xdt (xarray DataTree): input datasets.
        plot_inputs (dict): user inputs for plot
        logger (graphviper logger): logger
    Returns: selected xarray Dataset of visibility component and updated selection
    '''
    raster_xdt = _select_raster_ps_xdt(ps_xdt, plot_inputs, logger)

    # Create xds from concat ms_xds in ps
    raster_xds = concat_ps_xdt(raster_xdt, logger)

    data_group = plot_inputs['selection']['data_group_name'] if ('selection' in plot_inputs and 'data_group_name' in plot_inputs['selection']) else plot_inputs['auto_data_group']
    correlated_data = get_correlated_data(raster_xds, data_group)
    if raster_xds[correlated_data].count() == 0:
        raise RuntimeError("Plot failed: raster plane selection yielded data with all nan values.")

    # Set complex component of vis data
    raster_xds[correlated_data] = get_axis_data(raster_xds,
        plot_inputs['vis_axis'],
        data_group
    )

    # Convert float time to datetime
    set_datetime_coordinate(raster_xds)

    # Apply aggregator
    raster_xds = aggregate_data(raster_xds, plot_inputs, logger)

    logger.debug(f"Plotting visibility data with shape: {raster_xds[correlated_data].shape}")
    return raster_xds

def _select_raster_ps_xdt(ps_xdt, plot_inputs, logger):
    ''' Select default dimensions if needed for raster data '''
    # Determine which dims must be selected, add to selection, and do selection
    dims_to_select = _get_raster_selection_dims(plot_inputs)
    if not dims_to_select:
        return ps_xdt

    selection = plot_inputs['selection'] if 'selection' in plot_inputs else None
    dim_selection = {}

    for dim in dims_to_select:
        # Select first value (by index) and add to dim selection, or apply iter_axis value
        if not selection or dim not in selection:
            dim_selection[dim] = _get_first_dim_value(ps_xdt, dim, plot_inputs, logger)
        elif 'iter_axis' in plot_inputs and dim == plot_inputs['iter_axis']:
            dim_selection[dim] = selection[dim]
    if dim_selection:
        # Remove from selection for next plot
        if 'iter_axis' in plot_inputs and plot_inputs['iter_axis']:
            selection.pop(plot_inputs['iter_axis'])
        logger.info(f"Applying raster plane selection (using first index or iter value): {dim_selection}")
        plot_inputs['dim_selection'] = dim_selection
        return select_ms(ps_xdt, logger, **dim_selection)
    return ps_xdt

def _get_raster_selection_dims(plot_inputs):
    ''' Return which dimensions should be selected for raster plot.
        List of dimensions which are not x, y, or agg axis. '''
    data_dims = plot_inputs['data_dims'].copy()
    if plot_inputs['x_axis'] in data_dims:
        data_dims.remove(plot_inputs['x_axis'])
    if plot_inputs['y_axis'] in data_dims:
        data_dims.remove(plot_inputs['y_axis'])
    if plot_inputs['aggregator'] and plot_inputs['agg_axis']:
        for axis in plot_inputs['agg_axis']:
            data_dims.remove(axis)
    return data_dims

def _get_first_dim_value(ps_xdt, dim, plot_inputs, logger):
    ''' Return value of first dimension by index for polarization or by value for others. '''
    # If iter_axis, get first dim value after iter value is selected to avoid empty selected ps
    iter_ps = ps_xdt
    if 'iter_axis' in plot_inputs and plot_inputs['iter_axis']:
        iter_axis = plot_inputs['iter_axis']
        iter_selection = {iter_axis: plot_inputs['selection'][iter_axis]}
        logger.debug(f"Applying {iter_axis} iter_axis selection to select first {dim} value")
        iter_ps = select_ms(ps_xdt, logger, **iter_selection)

    values = []
    if dim == "polarization":
        # Get sorted list of polarization ids used
        stokes = list(stokes_types.values())
        for ms_xdt in iter_ps.values():
            for val in ms_xdt.polarization.values:
                values.append(stokes.index(val))
        sorted_values = sorted(list(set(values)))
        # Get pol name for pol id
        return stokes[sorted_values[0]]

    if dim == 'baseline':
        for ms_xdt in iter_ps.values():
            ant1_names = ms_xdt.baseline_antenna1_name.values
            ant2_names = ms_xdt.baseline_antenna2_name.values
            for baseline_id in ms_xdt.baseline_id.values:
                values.append(ant1_names[baseline_id] + " & " + ant2_names[baseline_id])
            return sorted(list(set(values)))[0]

    # Get sorted values list
    for ms_xdt in iter_ps.values():
        values.extend(ms_xdt[dim].values.tolist())
    return sorted(list(set(values)))[0]

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
    if not plot_inputs['aggregator']:
        return xds

    aggregator = plot_inputs['aggregator']
    agg_axis = plot_inputs['agg_axis']
    agg_xds = xds

    # Check if agg axes have been selected (selection or iteration) and are no longer a dimension
    apply_agg_axis = [axis for axis in agg_axis if axis in xds.dims]
    logger.debug(f"Applying {aggregator} to {apply_agg_axis}.")

    if aggregator == 'max':
        agg_xds = xds.max(dim=apply_agg_axis, keep_attrs=True)
    elif aggregator == 'mean':
        agg_xds = xds.mean(dim=apply_agg_axis, keep_attrs=True)
    elif aggregator == 'median':
        agg_xds = xds.median(dim=apply_agg_axis, keep_attrs=True)
    elif aggregator == 'min':
        agg_xds = xds.min(dim=apply_agg_axis, keep_attrs=True)
    elif aggregator == 'std':
        agg_xds = xds.std(dim=apply_agg_axis, keep_attrs=True)
    elif aggregator == 'sum':
        agg_xds = xds.sum(dim=apply_agg_axis, keep_attrs=True)
    elif aggregator == 'var':
        agg_xds = xds.var(dim=apply_agg_axis, keep_attrs=True)
    return agg_xds
