'''
Functions to create a raster xarray Dataset of visibility/spectrum data from xradio ProcessingSet
'''

import time

import numpy as np
import xarray as xr

from xradio.measurement_set.processing_set import ProcessingSet
from xradio.measurement_set._utils._utils.stokes_types import stokes_types

from ._ps_concat import concat_ps_xds
from ._ps_coords import set_datetime_coordinate
from ._ps_select import select_ps
from ._xds_data import get_axis_data

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
    return raster_xds, updated_selection

def _select_raster_ps(ps, plot_inputs, logger):
    ''' Select default dimensions if needed for raster data '''
    # Determine which dims must be selected, add to selection, and do selection
    input_selection = plot_inputs['selection']
    iter_axis = plot_inputs['iter_axis']

    dims_to_select = _get_raster_selection_dims(ps, plot_inputs)

    if dims_to_select:
        dim_selection = {}
        for dim in dims_to_select:
            # Select first value (by index) and add to input selection, or apply iter_axis value
            # (user selection would have been applied previously)
            if dim not in input_selection:
                input_selection[dim] = _get_first_dim_value(ps, dim)
                dim_selection[dim] = input_selection[dim]
            else:
                dim_selection[dim] = input_selection[dim]
        if dim_selection:
            logger.info(f"Applying default raster plane selection (using first index or iter value): {dim_selection}")
            return select_ps(ps, dim_selection, logger), input_selection
    return ps, input_selection

def _get_raster_selection_dims(ps, plot_inputs):
    data_dims = list(ps.get(0)[plot_inputs['correlated_data']].dims)
    print("data dims:", data_dims)
    if plot_inputs['x_axis'] in data_dims:
        data_dims.remove(plot_inputs['x_axis'])
    if plot_inputs['y_axis'] in data_dims:
        data_dims.remove(plot_inputs['y_axis'])
    if plot_inputs['agg_axis']:
        print("input agg axis:", plot_inputs['agg_axis'])
        for axis in plot_inputs['agg_axis']:
            print("remove agg axis:", axis)
            data_dims.remove(axis)
    return data_dims

def _get_first_dim_value(ps, dim):
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
    else:
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
    aggregator = plot_inputs['aggregator']
    agg_axis = plot_inputs['agg_axis']
    logger.debug(f"Applying {aggregator} to {agg_axis}.")
    if aggregator == 'max':
        return xds.max(dim=agg_axis, keep_attrs=True)
    if aggregator == 'mean':
        return xds.mean(dim=agg_axis, keep_attrs=True)
    if aggregator == 'median':
        return xds.median(dim=agg_axis, keep_attrs=True)
    if aggregator == 'min':
        return xds.min(dim=agg_axis, keep_attrs=True)
    if aggregator == 'std':
        return xds.std(dim=agg_axis, keep_attrs=True)
    if aggregator == 'sum':
        return xds.sum(dim=agg_axis, keep_attrs=True)
    if aggregator == 'var':
        return xds.var(dim=agg_axis, keep_attrs=True)
