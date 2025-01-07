'''
Functions to create a raster plot of visibility/spectrum data from xarray Dataset
'''

import hvplot.xarray
import hvplot.pandas
import numpy as np

from ._plot_axes import get_coordinate_labels, get_axis_labels, get_vis_axis_labels
from ..data.measurement_set._ms_data import get_correlated_data

def raster_plot_params(xds, x_axis, y_axis, vis_axis, data_group, selection, title, ms_name, color_limits):
    '''
    Create raster plot for vis axis.
        xds (xarray Dataset): selected dataset of MSv4 data to plot
        x_axis (str): x-axis to plot
        y_axis (str): y-axis to plot
        vis_axis (str): visibility component to plot (amp, phase, real, imag)
        data_group (str): xds data group name of correlated data, flags, weights, and uvw
        selection (dict): selection used for plot title
        title (str): title for plot, or None
        ms_name (str): base name of ms/zarr filename used for plot title
        color_limits (tuple): color limits (min, max) for plotting amplitude else (None, None)

    Returns: holoviews Image or Overlay (if flagged data)
    '''
    plot_params = {}
    plot_params['correlated_data'] = get_correlated_data(xds, data_group)
    plot_params['title'] = title if title is not None else _get_plot_title(xds, selection, ms_name)
    plot_params['x_axis_labels'] = get_axis_labels(xds, x_axis)
    plot_params['y_axis_labels'] = get_axis_labels(xds, y_axis)
    plot_params['c_axis_labels'] = get_vis_axis_labels(xds, data_group, vis_axis)
    plot_params['color_limits'] = color_limits
    return plot_params

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

def raster_plot(xds, plot_params):
    ''' Create raster plot for input xarray Dataset and plot params.
        Returns Overlay if combined unflagged/flagged plot or single Quadmesh/Scatter plot.
    '''
    # Plot parameters
    correlated_data = plot_params['correlated_data']
    x_axis, x_label, x_ticks = plot_params['x_axis_labels']
    y_axis, y_label, y_ticks = plot_params['y_axis_labels']
    c_axis, c_label = plot_params['c_axis_labels']
    title = plot_params['title']
    color_limits = plot_params['color_limits']

    # Set plot axes to numeric coordinates and add string coords as hover columns
    _set_index_coordinates(xds, x_axis, y_axis)

    # Unflagged and flagged data
    unflagged_xda = xds[correlated_data].where(xds.FLAG == 0.0).rename(c_axis.capitalize())
    flagged_xda = xds[correlated_data].where(xds.FLAG == 1.0).rename("Flagged_" + c_axis.capitalize())

    # Plot data
    # holoviews colormaps: https://holoviews.org/user_guide/Colormaps.html
    flagged_plot = _plot_xda(flagged_xda, x_axis, y_axis, color_limits, title, x_label, y_label, "Flagged " + c_label, x_ticks, y_ticks, "kr")
    unflagged_plot = _plot_xda(unflagged_xda, x_axis, y_axis, color_limits, title, x_label, y_label, c_label, x_ticks, y_ticks, "viridis")

    # Return combined plots or single plot
    if flagged_plot and unflagged_plot:
        return flagged_plot * unflagged_plot.opts(colorbar_position='left')
    elif unflagged_plot:
        return unflagged_plot
    else:
        return flagged_plot

def _plot_xda(xda, x_axis, y_axis, color_limits, title, x_label, y_label, c_label, x_ticks, y_ticks, colormap):
    # Returns Quadmesh plot if raster 2D data, Scatter plot if raster 1D data, or None if no data
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
            rot=90, xticks=x_ticks, yticks=y_ticks, marker='s',
        )

def _set_index_coordinates(xds, x_axis, y_axis):
    ''' Replace string coords with index for x and y axis '''
    if "polarization" in (x_axis, y_axis):
        xds["polarization"] = np.array(range(xds.polarization.size))
    if "baseline" in (x_axis, y_axis):
        xds["baseline"] = np.array(range(xds.baseline.size))
