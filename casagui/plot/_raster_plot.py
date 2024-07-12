'''
Functions to create a raster plot of visibilities from xradio processing_set
'''

import dask
import hvplot.xarray
import hvplot.pandas
import numpy as np
import os.path
import xarray as xr

from xradio.vis._processing_set import processing_set

from ..data._ps_utils import concat_ps_xds
from ..data._vis_data import get_vis_data_var, get_axis_data
from ..data._vis_stats import calculate_coord_min
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
    vis_data = get_vis_data_var(vis_axis)
    vis_dims = ps.get(0)[vis_data].dims
    selected_ps = _apply_selection(ps, vis_dims, selection, vis_path, logger)

    # Select raster plane (first index) if user did not
    select_dims = _get_non_axis_dims(vis_dims, x_axis, y_axis)
    raster_ps, selection = _select_raster_plane(selected_ps, select_dims, selection, vis_path, logger)

    # xds for raster plot
    raster_xds = concat_ps_xds(raster_ps, logger)

    # Set title for all plots
    title = _get_plot_title(raster_xds, select_dims, selection, os.path.basename(vis_path))

    # Calculate complex component of vis data
    raster_xds[vis_data] = get_axis_data(raster_xds, vis_axis)

    # Axes for plot (replaced with index for regular spacing where needed)
    raster_xds, x_axis_labels = get_axis_labels(raster_xds, x_axis)
    raster_xds, y_axis_labels = get_axis_labels(raster_xds, y_axis)
    c_axis_labels = get_vis_axis_labels(raster_xds, vis_data, vis_axis)

    return _plot_xds(raster_xds, vis_data, title, x_axis_labels, y_axis_labels, c_axis_labels, color_limits)

def _get_non_axis_dims(vis_dims, x_axis, y_axis):
    dims = list(vis_dims)
    dims.remove(x_axis)
    dims.remove(y_axis)
    return dims

def _apply_selection(ps, vis_dims, selection, vis_path, logger):
    ''' Apply dimension selection, metadata selection done previously '''
    if selection is None:
        return ps

    dim_selection = {}
    for key in selection:
        if key in vis_dims:
            value = selection[key]
            if isinstance(value, int): # convert index selection to value
                value = _get_value_for_index(ps, vis_path, key, value)
            dim_selection[key] = value
    if not dim_selection:
        return ps

    logger.info(f"Applying user selection to data dimensions: {dim_selection}")
    selected_ps = {}
    for key in ps:
        try:
            selected_ps[key] = ps[key].sel(dim_selection)
        except KeyError as e:
            pass
    if not selected_ps:
        raise RuntimeError("User selection yielded empty processing set.")
    return processing_set(selected_ps)

def _select_raster_plane(ps, select_dims, selection, vis_path, logger):
    ''' Select first index of unselected raster plane dims, add to selection '''
    dim_selection = {}
    for dim in select_dims:
        if dim not in selection:
            # select first
            selection[dim] = 0
            dim_selection[dim] = _get_value_for_index(ps, vis_path, dim, 0)
    if not dim_selection:
        return ps, selection

    logger.info(f"Applying raster plane selection (first index of unselected dimensions): {dim_selection}")
    selected_ps = {}
    for key in ps:
        try:
            selected_ps[key] = ps[key].sel(dim_selection)
        except KeyError as e:
            pass
    if not selected_ps:
        raise RuntimeError("Raster plane selection yielded empty processing set. Please select dimensions.")
    return processing_set(selected_ps), selection

def _get_value_for_index(ps, vis_path, dim, index):
    dim_list = []
    for key in ps:
        dim_list.append(ps[key][dim])
    dim_xda = xr.concat(dim_list, dim=dim)

    try:
        return np.unique(np.sort(dim_xda.values))[index]
    except IndexError:
        raise IndexError(f"{dim} selection {index} out of range")

def _get_plot_title(xds, selected_dims, selection, vis_name):
    ''' Form string containing vis name and selected values '''
    title = f"{vis_name}\n"

    # Add processing set selection: ddi, field, and intent
    if selection:
        if 'ddi' in selection.keys():
            title += f"ddi: {selection['ddi']} "
        if 'field' in selection.keys():
            field = selection['field']
            if isinstance(field, int):
                title += f"field: {xds.VISIBILITY.attrs['field_info']['name']} ({field}) "
            else:
                title += f"field: {field} "
        if 'intent' in selection.keys():
            title += f"intent: {selection['intent']} "
        if title[-1] != '\n':
            title += '\n'

    # Add selected dimensions to title: name (index)
    for dim in selected_dims:
        label = get_coordinate_label(xds, dim)
        index = selection[dim] if (dim in selection.keys() and isinstance(selection[dim], int)) else None
        title += f"{dim}: {label}"

        if index is not None:
            index_label = f" (ch {index}) " if dim == 'frequency' else f" ({index}) "
            title += index_label
        title += "\n"

    return title

def _plot_xds(xds, vis_data, title, x_axis_labels, y_axis_labels, c_axis_labels, color_limits, show_flagged = True):
    # create holoviews.element.raster.Image
    x_axis, x_label, x_ticks = x_axis_labels
    y_axis, y_label, y_ticks = y_axis_labels
    c_axis, c_label = c_axis_labels

    flagged_xda = xds[vis_data].where(xds.FLAG == 1.0).rename(c_axis)
    unflagged_xda = xds[vis_data].where(xds.FLAG == 0.0).rename(c_axis)

    # holoviews colormaps: https://holoviews.org/user_guide/Colormaps.html
    flagged_colormap = "kr"
    unflagged_colormap = "viridis"

    # Plot flagged data
    flagged = _plot_xda(flagged_xda, x_axis, y_axis, color_limits, "Flagged " + c_label, title, x_label, y_label, x_ticks, y_ticks, flagged_colormap)
    # Plot unflagged data (hover shows values in last plot)
    unflagged = _plot_xda(unflagged_xda, x_axis, y_axis, color_limits, c_label, title, x_label, y_label, x_ticks, y_ticks, unflagged_colormap)

    if flagged and unflagged:
        return flagged * unflagged.opts(colorbar_position='left')
    elif unflagged:
        return unflagged
    else:
        return flagged

def _plot_xda(xda, x_axis, y_axis, color_limits, c_label, title, x_label, y_label, x_ticks, y_ticks, colormap):
    if xda.count() == 0:
        return None

    if xda.coords[x_axis].size > 1 and xda.coords[y_axis].size > 1:
        # Raster 2D data
        return xda.hvplot.quadmesh(x=x_axis, y=y_axis, width=900, height=600,
            clim=color_limits, cmap=colormap, clabel=c_label,
            title=title, xlabel=x_label, ylabel=y_label,
            rot=90, xticks=x_ticks, yticks=y_ticks,
        )
    else:
        # Cannot raster 1D data, use scatter
        df = xda.to_dataframe().reset_index() # convert x and y axis from index to column
        return df.hvplot.scatter(
            x=x_axis, y=y_axis, c=xda.name, width=600, height=600,
            clim=color_limits, cmap=colormap, clabel=c_label,
            title=title, xlabel=x_label, ylabel=y_label,
            rot=90, xticks=x_ticks, yticks=y_ticks, marker='s'
        )
