'''
Functions to create a raster xarray Dataset of visibility/spectrum data from xradio ProcessingSet
'''

import numpy as np
import xarray as xr

from xradio.measurement_set.processing_set import ProcessingSet
from xradio.measurement_set._utils._utils.stokes_types import stokes_types

from ._ms_concat import concat_ps_xds
from ._ms_data import get_correlated_data, get_axis_data
from ._ms_select import select_ps

def raster_data(ps, x_axis, y_axis, vis_axis, data_group, selection, logger):
    '''
    Create raster xds: y_axis vs x_axis for vis axis.
        ps (xradio ProcessingSet): input MSv4 datasets
        x_axis (str): x-axis to plot
        y_axis (str): y-axis to plot
        vis_axis (str): visibility component to plot (amp, phase, real, imag)
        selection (dict): selected data dimensions (time, baseline, channel, polarization)
        logger (graphviper logger): logger
    Returns: selected xarray Dataset of visibility component and updated selection
    '''
    correlated_data = get_correlated_data(ps.get(0), data_group)
    raster_ps, selection = _select_raster_ps(ps, x_axis, y_axis, selection, data_group, correlated_data, logger)

    # Create xds from concat ms_xds in ps
    raster_xds = concat_ps_xds(raster_ps, logger)
    if raster_xds[correlated_data].count() == 0:
        raise RuntimeError("Plot failed: raster plane selection yielded data with all nan values.")

    # Set complex component of vis data
    raster_xds[correlated_data] = get_axis_data(raster_xds, vis_axis, data_group)

    logger.debug(f"Plotting visibility data with shape: {raster_xds[correlated_data].shape}")
    return raster_xds, selection

def _select_raster_ps(ps, x_axis, y_axis, selection, data_group, correlated_data, logger):
    ''' Apply user selection and select default dimensions if needed for raster data '''
    # Apply user selection first
    selected_ps = select_ps(ps, selection, data_group, logger)

    # Determine dims which must be selected
    data_dims = ps.get(0)[correlated_data].dims
    dims_to_select = _get_raster_selection_dims(data_dims, x_axis, y_axis)

    dim_selection = {}

    for dim in dims_to_select:
        if dim not in selection:
            selection[dim] = _get_first_dim_value(ps, dim)
            dim_selection[dim] = selection[dim]
    logger.info(f"Applying default raster plane selection (using first index): {dim_selection}")

    return select_ps(ps, selection, data_group, logger), selection

def _get_raster_selection_dims(data_dims, x_axis, y_axis):
    dims = list(data_dims)
    if x_axis in dims:
        dims.remove(x_axis)
    if y_axis in dims:
        dims.remove(y_axis)
    return dims

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
