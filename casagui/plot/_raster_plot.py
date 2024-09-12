'''
Functions to create a raster plot of visibilities from xradio processing_set
'''

import hvplot.xarray
import hvplot.pandas
import os.path

from xradio.vis._processing_set import processing_set

from ..data.vis_data._xds_utils import concat_ps_xds
from ..data.vis_data._vis_data import get_vis_data_var, get_axis_data
from ._plot_axes import get_coordinate_label, get_axis_labels, get_vis_axis_labels

def raster_plot(ps, x_axis, y_axis, vis_axis, selection, vis_path, color_limits, logger):
    '''
    Create raster plot y_axis vs x_axis for vis axis in ddi.
        ps (xradio processing set): dict of msv4 xarray Datasets containing vis data
        x_axis (str): x-axis to plot
        y_axis (str): y-axis to plot
        vis_axis (str): visibility component to plot (amp, phase, real, imag)
        selection (dict): select ddi, field, intent, time/baseline/channel/correlation
        vis_path (str): path to visibility file
        color_limits (tuple): color limits (min, max) for plotting amplitude

    Returns: holoviews Image or Overlay (if flagged data)
    '''
    vis_data_var = get_vis_data_var(ps, vis_axis)
    if 'SPECTRUM' in vis_data_var:
        x_axis = 'antenna_name' if x_axis in ['baseline', 'antenna'] else x_axis
        y_axis = 'antenna_name' if y_axis in ['baseline', 'antenna'] else y_axis

    # capture all dimensions before selection
    vis_dims = ps.get(0)[vis_data_var].dims
    dims_to_select = _get_raster_selection_dims(vis_dims, x_axis, y_axis)
    logger.debug(f"Selecting dimensions {dims_to_select} for raster plane")

    # xds selected for raster plane with vis data (amp, phase, etc.) set
    plot_xds, selection = _get_plot_xds(ps, x_axis, y_axis, vis_axis, vis_data_var, dims_to_select, selection, logger)
    logger.debug(f"Plotting visibility data with shape: {plot_xds[vis_data_var].shape}")

    # Set title for all plots
    title = _get_plot_title(plot_xds, dims_to_select, selection, os.path.basename(vis_path))

    # Axes for plot (replaced with index for regular spacing where needed)
    raster_xds, x_axis_labels = get_axis_labels(plot_xds, x_axis)
    raster_xds, y_axis_labels = get_axis_labels(plot_xds, y_axis)
    c_axis_labels = get_vis_axis_labels(plot_xds, vis_data_var, vis_axis)

    return _plot_xds(plot_xds, vis_data_var, title, x_axis_labels, y_axis_labels, c_axis_labels, color_limits)

def _get_plot_xds(ps, x_axis, y_axis, vis_axis, vis_data_var, dims_to_select, selection, logger):
    # User selection
    selected_ps = _apply_user_selection(ps, dims_to_select, selection, logger)

    # Raster plane selection (first index) if not selected by user; selection updated
    raster_ps, selection = _apply_raster_selection(selected_ps, dims_to_select, selection, logger)

    # xds for raster plot
    raster_xds = concat_ps_xds(raster_ps, logger)
    if raster_xds[vis_data_var].count() == 0:
        raise RuntimeError("Plot failed: raster plane selection yielded visibilities with nan values.")

    # Calculate complex component of vis data
    raster_xds[vis_data_var] = get_axis_data(raster_xds, vis_axis)

    return raster_xds, selection

def _get_raster_selection_dims(vis_dims, x_axis, y_axis):
    dims = list(vis_dims)
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
    ''' Return processing set of msxds where selection is applied.
        Exclude msxds where selection cannot be applied.
        Caller should check for empty ps.
    '''
    sel_ps = processing_set()
    for key, val in ps.items():
        try:
            sel_ps[key] = val.sel(**selection)
        except KeyError:
            pass
    return sel_ps

def _get_value_for_index(ps, dim, index):
    if dim == "polarization":
        # Do not sort alphabetically
        # Use predefined list from casacore StokesTypes for order
        polarizations = ['I', 'Q', 'U', 'V',
            'RR', 'RL', 'LR', 'LL', 'XX', 'XY', 'YX', 'YY',
            'RX', 'RY', 'LX', 'LY', 'XR', 'XL', 'YR', 'YL',
            'RCircular', 'LCircular', 'Linear', 'Ptotal',
            'Plinear', 'PFtotal', 'PFlinear', 'Pangle'
        ]
        # Get sorted _index_ list of polarizations used
        idx_list = []
        for key in ps:
            for pol in ps[key].polarization.values:
                idx_list.append(polarizations.index(pol))
        sorted_idx = sorted(list(set(idx_list)))
        try:
            # Select index from sorted index list
            selected_idx = sorted_idx[index]
            # Return polarization for index
            return polarizations[selected_idx]
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

def _get_plot_title(xds, selected_dims, selection, vis_name):
    ''' Form string containing vis name and selected values '''
    title = f"{vis_name}\n"

    # Add processing set selection: spw, field, and intent
    if 'spw_name' in selection:
        title += f"spw: {selection['spw_name']} ({xds.frequency.spectral_window_id})\n"
    if 'field_name' in selection:
        title += f"field: {selection['field_name']}\n"
    if 'source_name' in selection:
        title += f"source: {selection['source_name']}\n"
    if 'obs_mode' in selection:
        title += f"obs mode: {selection['obs_mode']}\n"

    # Add selected dimensions to title: name (index)
    for dim in selected_dims:
        label = get_coordinate_label(xds, dim)
        index = selection[dim] if (dim in selection and isinstance(selection[dim], int)) else None
        title += f"{dim}: {label}"

        if index is not None:
            index_label = f" (ch {index}) " if dim == 'frequency' else f" ({index}) "
            title += index_label
        title += "\n"

    return title

def _plot_xds(xds, vis_data_var, title, x_axis_labels, y_axis_labels, c_axis_labels, color_limits, show_flagged = True):
    # create holoviews.element.raster.Image
    x_axis, x_label, x_ticks = x_axis_labels
    y_axis, y_label, y_ticks = y_axis_labels
    c_axis, c_label = c_axis_labels

    unflagged_xda = xds[vis_data_var].where(xds.FLAG == 0.0).rename(c_axis)
    flagged_xda = xds[vis_data_var].where(xds.FLAG == 1.0).rename(c_axis)

    # holoviews colormaps: https://holoviews.org/user_guide/Colormaps.html
    unflagged_colormap = "viridis"
    flagged_colormap = "kr"

    # Plot flagged data
    flagged_plot = _plot_xda(flagged_xda, x_axis, y_axis, color_limits, "Flagged " + c_label, title, x_label, y_label, x_ticks, y_ticks, flagged_colormap)
    # Plot unflagged data (hover shows values in last plot)
    unflagged_plot = _plot_xda(unflagged_xda, x_axis, y_axis, color_limits, c_label, title, x_label, y_label, x_ticks, y_ticks, unflagged_colormap)

    if flagged_plot and unflagged_plot:
        return flagged_plot * unflagged_plot.opts(colorbar_position='left')
    elif unflagged_plot:
        return unflagged_plot
    else:
        return flagged_plot

def _plot_xda(xda, x_axis, y_axis, color_limits, c_label, title, x_label, y_label, x_ticks, y_ticks, colormap):
    if xda.count() == 0:
        return None
    #print("plot xda:", xda)

    if xda.coords[x_axis].size > 1 and xda.coords[y_axis].size > 1:
        # Raster 2D data
        return xda.hvplot.quadmesh(x=x_axis, y=y_axis, width=900, height=600,
            clim=color_limits, cmap=colormap, clabel=c_label,
            title=title, xlabel=x_label, ylabel=y_label,
            rot=90, xticks=x_ticks, yticks=y_ticks,
        )
    else:
        # Cannot raster 1D data, use scatter from pandas dataframe
        df = xda.to_dataframe().reset_index() # convert x and y axis from index to column
        return df.hvplot.scatter(
            x=x_axis, y=y_axis, c=xda.name, width=600, height=600,
            clim=color_limits, cmap=colormap, clabel=c_label,
            title=title, xlabel=x_label, ylabel=y_label,
            rot=90, xticks=x_ticks, yticks=y_ticks, marker='s'
        )
