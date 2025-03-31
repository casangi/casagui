'''
Functions to create a raster plot of visibility/spectrum data from xarray Dataset
'''

from bokeh.models import HoverTool
import holoviews as hv
import numpy as np
import hvplot.xarray
import hvplot.pandas

from ._xds_plot_axes import get_coordinate_labels, get_axis_labels, get_vis_axis_labels
from casagui.bokeh.format import get_time_formatter
from casagui.data.measurement_set._ps_coords import set_index_coordinates

def raster_plot_params(xds, plot_inputs):
    '''
    Get parameters needed for raster plot.
        xds (xarray Dataset): selected dataset of MSv4 data to plot
        plot_inputs (dict): user inputs to plot.
    Returns: dict
    '''
    plot_params = {}
    plot_params['correlated_data'] = plot_inputs['correlated_data']
    plot_params['color_limits'] = plot_inputs['color_limits']
    plot_params['aggregator'] = plot_inputs['aggregator']

    if plot_inputs['title']: 
        plot_params['title'] = plot_inputs['title']
    else:
        plot_params['title'] = _get_plot_title(xds, plot_inputs)

    plot_params['x_axis_labels'] = get_axis_labels(xds, plot_inputs['x_axis'])
    plot_params['y_axis_labels'] = get_axis_labels(xds, plot_inputs['y_axis'])
    plot_params['c_axis_labels'] = _get_vis_axis_labels(xds, plot_inputs)
    return plot_params

def _get_plot_title(xds, plot_inputs):
    ''' Form string containing ms name and selected values '''
    selection = plot_inputs['selection']
    data_dims = plot_inputs['data_dims']
    ms_name = plot_inputs['ms_basename']

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
            ps_selection.append(f"intents: {selection[key]}")
        elif key == 'data_group':
            continue # do not include?
        elif key in data_dims:
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

def _get_vis_axis_labels(xds, plot_inputs):
    data_group = plot_inputs['selection']['data_group']
    correlated_data = plot_inputs['correlated_data']
    vis_axis = plot_inputs['vis_axis']
    aggregator = plot_inputs['aggregator']
    axis, label = get_vis_axis_labels(xds, data_group, correlated_data, vis_axis)
    if aggregator:
        label = " ".join([aggregator.capitalize(), label])
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
    xds = set_index_coordinates(xds, (x_axis, y_axis))

    # Unflagged and flagged data.  Use same name, for histogram dimension.
    if aggregator: 
        xda_name = "_".join([aggregator, c_axis])
    else:
        xda_name = c_axis
    flagged_name = "flagged_" + xda_name
    xda = xds[correlated_data].where(xds.FLAG == 0.0).rename(xda_name)
    flagged_xda = xds[correlated_data].where(xds.FLAG == 1.0).rename(flagged_name)

    # Plot data
    # holoviews colormaps: https://holoviews.org/user_guide/Colormaps.html
    unflagged_plot = None
    flagged_plot = None
    try:
        if xda.count() > 0:
            unflagged_plot = _plot_xda(xda, x_axis, y_axis, xda_name, color_limits, title, x_label, y_label, c_label, x_ticks, y_ticks, "viridis")
        if flagged_xda.count() > 0:
            flagged_plot = _plot_xda(flagged_xda, x_axis, y_axis, flagged_name, color_limits, title, x_label, y_label, "Flagged " + c_label, x_ticks, y_ticks, "reds")
    except Exception as e:
        print("Plot exception:", e)

    # Return Overlay plot or single QuadMesh plot
    if flagged_plot and unflagged_plot:
        plot = flagged_plot * unflagged_plot.opts(colorbar_position='left')
    elif unflagged_plot:
        plot = unflagged_plot.opts(colorbar_position='left')
    else:
        plot = flagged_plot

    return plot.opts(
       hv.opts.QuadMesh(tools=['hover']))

def _plot_xda(xda, x_axis, y_axis, c_axis, color_limits, title, x_label, y_label, c_label, x_ticks, y_ticks, colormap):
    # Returns Quadmesh plot if raster 2D data, Scatter plot if raster 1D data, or None if no data
    x_formatter = get_time_formatter() if x_axis == 'time' else None
    y_formatter = get_time_formatter() if y_axis == 'time' else None

    if xda[x_axis].size > 1 and xda[y_axis].size > 1:
        # Raster 2D data
        return xda.hvplot.quadmesh(x_axis, y_axis,
            clim=color_limits, cmap=colormap, clabel=c_label,
            title=title, xlabel=x_label, ylabel=y_label,
            xformatter=x_formatter, yformatter=y_formatter,
            rot=90, xticks=x_ticks, yticks=y_ticks,
            colorbar=True,
        )
    else:
        # Cannot raster 1D data, use scatter from pandas dataframe
        df = xda.to_dataframe().reset_index() # convert x and y axis from index to column
        return df.hvplot.scatter(
            x=x_axis, y=y_axis, c=c_axis,
            clim=color_limits, cmap=colormap, clabel=c_label,
            title=title, xlabel=x_label, ylabel=y_label,
            xformatter=x_formatter, yformatter=y_formatter,
            rot=90, xticks=x_ticks, yticks=y_ticks,
            marker='s', hover=True,
        )
