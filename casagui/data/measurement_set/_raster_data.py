'''
Functions to create a raster xarray Dataset of visibility/spectrum data from xradio ProcessingSet
'''

from xradio.measurement_set.processing_set import ProcessingSet
from xradio.measurement_set._utils._utils.stokes_types import stokes_types

from ._xds_utils import concat_ps_xds
from ._ms_data import get_vis_spectrum_data_var, get_axis_data

def raster_data(ps, x_axis, y_axis, vis_axis, selection, logger):
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
    data_var = get_vis_spectrum_data_var(ps, vis_axis)
    if 'SPECTRUM' in data_var:
        x_axis = 'antenna_name' if x_axis in ['baseline', 'antenna'] else x_axis
        y_axis = 'antenna_name' if y_axis in ['baseline', 'antenna'] else y_axis

    # capture all dimensions before selection
    data_dims = ps.get(0)[data_var].dims
    dims_to_select = _get_raster_selection_dims(data_dims, x_axis, y_axis)
    logger.debug(f"Selecting dimensions {dims_to_select} for raster plane")

    # xds selected for raster plane with visibility component (amp, phase, real, or imag)
    return _get_plot_xds(ps, x_axis, y_axis, vis_axis, data_var, dims_to_select, selection, logger)

def _get_plot_xds(ps, x_axis, y_axis, vis_axis, data_var, dims_to_select, selection, logger):
    # User selection
    selected_ps = _apply_user_selection(ps, dims_to_select, selection, logger)

    # Raster plane selection (first index) if not selected by user; selection updated
    raster_ps, selection = _apply_raster_selection(selected_ps, dims_to_select, selection, logger)

    # xds for raster plot
    raster_xds = concat_ps_xds(raster_ps, logger)
    if raster_xds[data_var].count() == 0:
        raise RuntimeError("Plot failed: raster plane selection yielded data with all nan values.")

    # Calculate complex component of vis data
    raster_xds[data_var] = get_axis_data(raster_xds, vis_axis)
    logger.debug(f"Plotting visibility data with shape: {raster_xds[data_var].shape}")

    return raster_xds, selection

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

    if not selected_ps:
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
    if not selected_ps:
        raise RuntimeError("Plot failed: default raster plane selection yielded empty processing set.")
    return selected_ps, selection | dim_selection

def _apply_xds_selection(ps, selection):
    ''' Return ProcessingSet of msxds where selection is applied.
        Exclude msxds where selection cannot be applied.
        Caller should check for empty ps.
    '''
    sel_ps = ProcessingSet()
    for key, val in ps.items():
        try:
            sel_ps[key] = val.sel(**selection)
        except KeyError:
            pass
    return sel_ps

def _get_value_for_index(ps, dim, index):
    if dim == "polarization":
        # Get sorted _index_ list of polarizations used
        pol_ids = list(stokes_types.keys())
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
