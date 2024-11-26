'''
Functions to create a raster plot of visibility/spectrum data from xarray Dataset
'''

import hvplot.xarray
import hvplot.pandas

from ._plot_axes import get_coordinate_labels, get_axis_labels, get_vis_axis_labels
from ..data.measurement_set._ms_data import get_correlated_data

def raster_plot(xds, x_axis, y_axis, vis_axis, data_group, selection, ms_name, color_limits):
    '''
    Create raster plot for vis axis.
        xds (xarray Dataset): selected dataset of MSv4 data to plot
        x_axis (str): x-axis to plot
        y_axis (str): y-axis to plot
        vis_axis (str): visibility component to plot (amp, phase, real, imag)
        data_group (str): xds data group name of correlated data, flags, weights, and uvw
        selection (dict): select ddi, field, intent, time/baseline/channel/correlation
        ms_name (str): base name of ms/zarr filename
        color_limits (tuple): color limits (min, max) for plotting amplitude

    Returns: holoviews Image or Overlay (if flagged data)
    '''
    # Set title for all plots
    title = _get_plot_title(xds, selection, ms_name)

    # Axes for plot (replaced with index for regular spacing where needed)
    xds, x_axis_labels = get_axis_labels(xds, x_axis)
    xds, y_axis_labels = get_axis_labels(xds, y_axis)
    correlated_data = get_correlated_data(xds, data_group)
    c_axis_labels = get_vis_axis_labels(xds, correlated_data, vis_axis)

    return _plot_xds(xds, correlated_data, title, x_axis_labels, y_axis_labels, c_axis_labels, color_limits)

def _get_plot_title(xds, selection, vis_name):
    ''' Form string containing vis name and selected values '''
    title = f"{vis_name}\n"

    metadata_selection = []
    dim_selections = []
    for key in selection:
        # Add processing set selection: spw, field, and intent
        if key == 'spw_name':
            metadata_selection.append(f"spw: {selection[key]} ({xds.frequency.spectral_window_id})")
        elif key == 'field_name':
            metadata_selection.append(f"field: {selection[key]}")
        elif key == 'source_name':
            metadata_selection.append(f"source: {selection[key]}")
        elif key == 'intent':
            metadata_selection.append(f"intent: {selection[key]}")
        else:
            # Add selected dimensions to title: name (index)
            label = get_coordinate_labels(xds, key)
            index = selection[key] if isinstance(selection[key], int) else None
            dim_selection = f"{key}: {label}"
            if index is not None:
                index_label = f" (ch {index}) " if key == 'frequency' else f" ({index}) "
                dim_selection += index_label
            dim_selections.append(dim_selection)
    title += '\n'.join(metadata_selection) + '\n'
    title += '  '.join(dim_selections)
    return title

def _plot_xds(xds, correlated_data, title, x_axis_labels, y_axis_labels, c_axis_labels, color_limits, show_flagged = True):
    # create holoviews.element.raster.Image
    x_axis, x_label, x_ticks = x_axis_labels
    y_axis, y_label, y_ticks = y_axis_labels
    c_axis, c_label = c_axis_labels

    unflagged_xda = xds[correlated_data].where(xds.FLAG == 0.0).rename(c_axis.capitalize())
    flagged_xda = xds[correlated_data].where(xds.FLAG == 1.0).rename("Flagged_" + c_axis.capitalize())

    # holoviews colormaps: https://holoviews.org/user_guide/Colormaps.html
    unflagged_colormap = "viridis"
    flagged_colormap = "kr"

    # Plot flagged data
    flagged_plot = _plot_xda(flagged_xda, x_axis, y_axis, color_limits, title, x_label, y_label, "Flagged " + c_label, x_ticks, y_ticks, flagged_colormap)
    # Plot unflagged data (hover shows values in last plot)
    unflagged_plot = _plot_xda(unflagged_xda, x_axis, y_axis, color_limits, title, x_label, y_label, c_label, x_ticks, y_ticks, unflagged_colormap)

    if flagged_plot and unflagged_plot:
        return flagged_plot * unflagged_plot.opts(colorbar_position='left')
    elif unflagged_plot:
        return unflagged_plot
    else:
        return flagged_plot

def _plot_xda(xda, x_axis, y_axis, color_limits, title, x_label, y_label, c_label, x_ticks, y_ticks, colormap):
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
