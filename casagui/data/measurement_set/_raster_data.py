'''
Functions to create a raster xarray Dataset of visibility/spectrum data from xradio ProcessingSet
'''

from xradio.measurement_set.processing_set import ProcessingSet
from xradio.measurement_set._utils._utils.stokes_types import stokes_types

from ._xds_utils import concat_ps_xds
from ._ms_data import get_correlated_data, get_axis_data

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
    # Select dimensions for raster data
    correlated_data = get_correlated_data(ps.get(0), data_group)
    raster_ps, selection = _select_ps(ps, x_axis, y_axis, correlated_data, selection, logger)

    # Create xds from concat ms_xds in ps
    raster_xds = concat_ps_xds(raster_ps, logger)
    if raster_xds[correlated_data].count() == 0:
        raise RuntimeError("Plot failed: raster plane selection yielded data with all nan values.")

    # Calculate complex component of vis data
    raster_xds[correlated_data] = get_axis_data(raster_xds, vis_axis, data_group)

    logger.debug(f"Plotting visibility data with shape: {raster_xds[correlated_data].shape}")
    return raster_xds, selection

def _select_ps(ps, x_axis, y_axis, correlated_data, selection, logger):
    ''' Select non-plot-axes dimensions to get raster plane '''
    # Determine dims which must be selected for raster plot
    data_dims = ps.get(0)[correlated_data].dims
    dims_to_select = _get_raster_selection_dims(data_dims, x_axis, y_axis)
    logger.debug(f"Selecting dimensions {dims_to_select} for raster plane")

    # Apply user dim selection 
    selected_ps = _apply_user_selection(ps, data_dims, selection, logger)

    # Apply selection using first index if not selected by user
    return _apply_raster_selection(selected_ps, dims_to_select, selection, logger)

def _get_raster_selection_dims(data_dims, x_axis, y_axis):
    dims = list(data_dims)
    if x_axis in dims:
        dims.remove(x_axis)
    if y_axis in dims:
        dims.remove(y_axis)
    return dims

def _apply_user_selection(ps, dims, selection, logger):
    ''' Apply dimension selection '''
    if selection is None:
        return ps

    dim_selection = {}

    for dim in dims:
        if dim in selection:
            value = selection[dim]
            if isinstance(value, int): # convert index selection to value
                value = _get_value_for_index(ps, dim, value)
            dim_selection[dim] = value

    # No user selection
    if not dim_selection:
        return ps

    # Select ps
    logger.info(f"Applying user selection to data dimensions: {dim_selection}")
    selected_ps = _apply_xds_selection(ps, dim_selection)

    if len(selected_ps) == 0:
        raise RuntimeError("Plot failed: user selection yielded empty processing set.")
    return selected_ps

def _apply_raster_selection(ps, dims, selection, logger):
    ''' Select first index of unselected raster plane dims, add to selection '''
    if not selection:
        selection = {}
    dim_selection = {}

    for dim in dims:
        if dim not in selection:
            dim_selection[dim] = _get_value_for_index(ps, dim, 0) # select first
    if not dim_selection:
        return ps, selection
    logger.info(f"Applying default raster plane selection (first index): {dim_selection}")
    selected_ps = _apply_xds_selection(ps, dim_selection)
    if len(selected_ps) == 0:
        raise RuntimeError("Plot failed: default raster plane selection yielded empty processing set.")
    return selected_ps, selection | dim_selection

def _apply_xds_selection(ps, selection):
    ''' Return ProcessingSet of ms_xds where selection is applied.
        Exclude ms_xds where selection cannot be applied (avoid exception in ps.ms_sel())
        Caller should check for empty ps.
    '''
    sel_ps = ProcessingSet()
    for name, xds in ps.items():
        try:
            sel_ps[name] = xds.sel(**selection)
        except KeyError:
            pass
    return sel_ps

def _get_value_for_index(ps, dim, index):
    if dim == "polarization":
        # Get sorted _index_ list of polarizations used
        pol_names = list(stokes_types.values())
        idx_list = []
        for key in ps:
            for pol in ps[key].polarization.values:
                idx_list.append(pol_names.index(pol))
        sorted_pol_idx = sorted(list(set(idx_list)))

        try:
            # Select index from sorted index list
            selected_pol_idx = sorted_pol_idx[index]
            # Return polarization for index
            return pol_names[selected_pol_idx]
        except IndexError:
            raise IndexError(f"Plot failed: {dim} selection {index} out of range {len(sorted_idx)}")
    else:
        # Get sorted values list
        values = []
        for key in ps:
            values.extend(ps[key][dim].values.tolist())
        values = sorted(list(set(values)))
        # Select index in sorted values list
        try:
            return values[index]
        except IndexError:
            raise IndexError(f"Plot failed: {dim} selection {index} out of range {len(values)}")
