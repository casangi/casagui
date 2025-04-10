'''
Functions to create a raster plot of visibility/spectrum data from xarray Dataset
'''

import holoviews as hv

# hvPlot extensions used to plot xarray DataArray and pandas DataFrame
# pylint: disable=unused-import
import hvplot.xarray
import hvplot.pandas
# pylint: enable=unused-import

from casagui.bokeh.format import get_time_formatter
from casagui.data.measurement_set.processing_set._ps_coords import set_index_coordinates
from casagui.plot._xds_plot_axes import get_axis_labels, get_vis_axis_labels
#from casagui.plot._xds_plot_axes import get_coordinate_labels, get_axis_labels, get_vis_axis_labels

def raster_plot_params(xds, plot_inputs):
    '''
    Get parameters needed for raster plot.
        xds (xarray Dataset): selected dataset of MSv4 data to plot
        plot_inputs (dict): user inputs to plot.
    Returns: dict
    '''
    plot_params = {}
    plot_params['correlated_data'] = plot_inputs['correlated_data']
    plot_params['aggregator'] = plot_inputs['aggregator']
    plot_params['colorbar'] = {}

    if plot_inputs['title']:
        plot_params['title'] = plot_inputs['title']
    else:
        plot_params['title'] = _get_plot_title(plot_inputs)

    x_axis_labels = get_axis_labels(xds, plot_inputs['x_axis'])
    y_axis_labels = get_axis_labels(xds, plot_inputs['y_axis'])
    c_axis_labels = _get_c_axis_labels(xds, plot_inputs)

    _set_axis_label_params(plot_params, 'x', x_axis_labels)
    _set_axis_label_params(plot_params, 'y', y_axis_labels)
    _set_axis_label_params(plot_params, 'c', c_axis_labels)
    return plot_params

def _get_plot_title(plot_inputs):
    ''' Form string containing ms name and selected values '''
    ms_name = plot_inputs['ms_basename']
    iter_axis = plot_inputs['iter_axis']
    selection = plot_inputs['selection']

    title = f"{ms_name}\n"

    # Add iter_axis selection
    if iter_axis and iter_axis in selection:
        title += f"{iter_axis} {selection[iter_axis]}"

    '''
    # Include complete selection?
    data_dims = plot_inputs['data_dims']
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
    '''
    return title

def _get_c_axis_labels(xds, plot_inputs):
    data_group = plot_inputs['selection']['data_group']
    correlated_data = plot_inputs['correlated_data']
    vis_axis = plot_inputs['vis_axis']
    aggregator = plot_inputs['aggregator']

    axis, label = get_vis_axis_labels(xds, data_group, correlated_data, vis_axis)
    if aggregator:
        label = " ".join([aggregator.capitalize(), label])
    return (axis, label, None)

def _set_axis_label_params(plot_params, axis, axis_labels):
    # Axis labels are (axis, label, ticks).
    if 'axis_labels' not in plot_params:
        plot_params['axis_labels'] = {}
    plot_params['axis_labels'][axis] = {}
    plot_params['axis_labels'][axis]['axis'] = axis_labels[0]
    plot_params['axis_labels'][axis]['label'] = axis_labels[1]
    plot_params['axis_labels'][axis]['ticks'] = axis_labels[2]

def raster_plot(xds, plot_params):
    ''' Create raster plot for input xarray Dataset and plot params.
        Returns Overlay if combined unflagged/flagged plot or single Quadmesh/Scatter plot.
    '''
    x_axis = plot_params['axis_labels']['x']['axis']
    y_axis = plot_params['axis_labels']['y']['axis']
    c_axis = plot_params['axis_labels']['c']['axis']

    # Set plot axes to numeric coordinates if needed
    xds = set_index_coordinates(xds, (x_axis, y_axis))

    # Unflagged and flagged data.  Use same name, for histogram dimension.
    # c axis labels are (axis, label)
    xda_name = c_axis
    if plot_params['aggregator']:
        xda_name = "_".join([plot_params['aggregator'], xda_name])
    xda = xds[plot_params['correlated_data']].where(xds.FLAG == 0.0).rename(xda_name)
    flagged_xda = xds[plot_params['correlated_data']].where(xds.FLAG == 1.0).rename("flagged_" + xda_name)

    # Plot data
    # holoviews colormaps: https://holoviews.org/user_guide/Colormaps.html
    unflagged_plot = _plot_xda(xda, plot_params, "viridis")
    if plot_params['colorbar']['unflagged']:
        unflagged_plot = unflagged_plot.opts(colorbar_position='left')
    flagged_plot = _plot_xda(flagged_xda, plot_params, "reds", True)

    # Return Overlay plot with hover tools
    return (flagged_plot * unflagged_plot).opts(
        hv.opts.QuadMesh(tools=['hover'])
    )

def _plot_xda(xda, plot_params, colormap, is_flagged=False):
    # Returns Quadmesh plot if raster 2D data, Scatter plot if raster 1D data, or None if no data
    x_axis = plot_params['axis_labels']['x']['axis']
    y_axis = plot_params['axis_labels']['y']['axis']
    c_label = plot_params['axis_labels']['c']['label']

    x_formatter = get_time_formatter() if x_axis == 'time' else None
    y_formatter = get_time_formatter() if y_axis == 'time' else None
    enable_colorbar = xda.count() > 0

    if is_flagged:
        c_label = "Flagged " + c_label
        plot_params['colorbar']['flagged'] = enable_colorbar
    else:
        plot_params['colorbar']['unflagged'] = enable_colorbar

    if xda[x_axis].size > 1 and xda[y_axis].size > 1:
        # Raster 2D data
        return xda.hvplot.quadmesh(
            x_axis,
            y_axis,
            clim=plot_params['color_limits'],
            cmap=colormap,
            clabel=c_label,
            title=plot_params['title'],
            xlabel=plot_params['axis_labels']['x']['label'],
            ylabel=plot_params['axis_labels']['y']['label'],
            xformatter=x_formatter,
            yformatter=y_formatter,
            xticks=plot_params['axis_labels']['x']['ticks'],
            yticks=plot_params['axis_labels']['y']['ticks'],
            rot=45, # angle for x axis labels
            colorbar=enable_colorbar,
        )

    # Cannot raster 1D data, use scatter from pandas dataframe
    df = xda.to_dataframe().reset_index() # convert x and y axis from index to column
    return df.hvplot.scatter(
        x=x_axis,
        y=y_axis,
        c=plot_params['axis_labels']['c']['axis'],
        clim=plot_params['color_limits'],
        cmap=colormap,
        clabel=c_label,
        title=plot_params['title'],
        xlabel=plot_params['axis_labels']['x']['label'],
        ylabel=plot_params['axis_labels']['y']['label'],
        xformatter=x_formatter,
        yformatter=y_formatter,
        xticks=plot_params['axis_labels']['x']['ticks'],
        yticks=plot_params['axis_labels']['y']['ticks'],
        rot=45,
        marker='s', # square
        hover=True,
    )
