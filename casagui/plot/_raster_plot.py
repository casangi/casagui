'''
Functions to create a raster plot of visibility/spectrum data from xarray Dataset
'''

import numpy as np
import hvplot.xarray
import hvplot.pandas

from ._plot_axes import get_coordinate_labels, get_axis_labels, get_vis_axis_labels, get_axis_formatters
from casagui.data.measurement_set._ms_coords import set_index_coordinates
from casagui.data.measurement_set._ms_data import get_correlated_data

def raster_plot_params(xds, x_axis, y_axis, vis_axis, data_group, selection, title, ms_name, color_limits, aggregator):
    '''
    Get parameters needed for raster plot.
        xds (xarray Dataset): selected dataset of MSv4 data to plot
        x_axis (str): x-axis to plot
        y_axis (str): y-axis to plot
        vis_axis (str): visibility component to plot (amp, phase, real, imag)
        data_group (str): xds data group name of correlated data, flags, weights, and uvw
        selection (dict): selection used for plot title
        title (str): title for plot, or None
        ms_name (str): base name of ms/zarr filename used for plot title
        color_limits (tuple): color limits (min, max) for plotting amplitude else (None, None)
        aggregator (str): 
    Returns: dict
    '''
    plot_params = {}
    plot_params['correlated_data'] = get_correlated_data(xds, data_group)
    plot_params['title'] = title if title is not None else _get_plot_title(xds, selection, ms_name)
    plot_params['x_axis_labels'] = get_axis_labels(xds, x_axis)
    plot_params['y_axis_labels'] = get_axis_labels(xds, y_axis)
    plot_params['c_axis_labels'] = _get_vis_axis_labels(xds, data_group, vis_axis, aggregator)
    plot_params['color_limits'] = color_limits
    plot_params['aggregator'] = aggregator
    return plot_params

def _get_plot_title(xds, selection, ms_name):
    ''' Form string containing ms name and selected values '''
    title = f"{ms_name}\n"

    ps_selection = []
    dim_selections = []
    for key in selection:
        # Add processing set selection: spw, field, and intent
        if key == 'spw_name':
            spw_selection = f"spw: {selection[key]}"
            if 'frequency' in xds:
                spw_selection += f" ({xds.frequency.spectral_window_id})"
            ps_selection.append(spw_selection)
        elif key == 'field_name':
            ps_selection.append(f"field: {selection[key]}")
        elif key == 'source_name':
            ps_selection.append(f"source: {selection[key]}")
        elif key == 'intents':
            ps_selection.append(f"intent: {selection[key]}")
        else:
            # Add selected dimensions to title: name (index)
            label = get_coordinate_labels(xds, key)
            index = selection[key] if isinstance(selection[key], int) else None
            dim_selection = f"{key}: {label}"
            if index is not None:
                index_label = f" (ch {index}) " if key == 'frequency' else f" ({index}) "
                dim_selection += index_label
            dim_selections.append(dim_selection)
    title += '\n'.join(ps_selection) + '\n'
    title += '  '.join(dim_selections)
    return title

def _get_vis_axis_labels(xds, data_group, vis_axis, aggregator):
    axis, label = get_vis_axis_labels(xds, data_group, vis_axis)
    if aggregator:
        label = aggregator.capitalize() + " " + label
    return (axis, label)

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
    aggregator = plot_params['aggregator']

    # Set plot axes to numeric coordinates if needed
    set_index_coordinates(xds, (x_axis, y_axis))

    # Unflagged and flagged data.  Use same name, for histogram dimension.
    if aggregator: 
        xda_name = "_".join([aggregator, c_axis])
    else:
        xda_name = c_axis
    unflagged_xda = xds[correlated_data].where(xds.FLAG == 0.0).rename(xda_name)
    flagged_xda = xds[correlated_data].where(xds.FLAG == 1.0).rename(xda_name)

    # Plot data
    # holoviews colormaps: https://holoviews.org/user_guide/Colormaps.html
    try:
        unflagged_plot = _plot_xda(unflagged_xda, x_axis, y_axis, color_limits, title, x_label, y_label, c_label, x_ticks, y_ticks, "viridis")
        flagged_plot = _plot_xda(flagged_xda, x_axis, y_axis, color_limits, title, x_label, y_label, "Flagged " + c_label, x_ticks, y_ticks, "reds")
    except Exception as e:
        print("Plot exception:", e)

    # Return combined plots or single plot
    if flagged_plot is not None and unflagged_plot is not None:
        return flagged_plot * unflagged_plot.opts(colorbar_position='left')
    elif unflagged_plot is not None:
        return unflagged_plot
    else:
        return flagged_plot

def _plot_xda(xda, x_axis, y_axis, color_limits, title, x_label, y_label, c_label, x_ticks, y_ticks, colormap):
    # Returns Quadmesh plot if raster 2D data, Scatter plot if raster 1D data, or None if no data
    if xda.count() == 0:
        return None

    # formatter is None unless time
    x_formatter, y_formatter = get_axis_formatters(x_axis, y_axis)

    if xda.coords[x_axis].size > 1 and xda.coords[y_axis].size > 1:
        # Raster 2D data
        return xda.hvplot.quadmesh(x=x_axis, y=y_axis,
            clim=color_limits, cmap=colormap, clabel=c_label,
            title=title, xlabel=x_label, ylabel=y_label,
            xformatter=x_formatter, yformatter=y_formatter,
            rot=90, xticks=x_ticks, yticks=y_ticks,
            hover=True, colorbar=True,
        )
    else:
        # Cannot raster 1D data, use scatter from pandas dataframe
        df = xda.to_dataframe().reset_index() # convert x and y axis from index to column
        return df.hvplot.scatter(
            x=x_axis, y=y_axis, c=xda.name,
            clim=color_limits, cmap=colormap, clabel=c_label,
            title=title, xlabel=x_label, ylabel=y_label,
            xformatter=x_formatter, yformatter=y_formatter,
            rot=90, xticks=x_ticks, yticks=y_ticks,
            marker='s',
        )
