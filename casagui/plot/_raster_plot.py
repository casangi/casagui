'''
Functions to create a raster plot of visibilities from xradio processing_set
'''

import dask
import hvplot.xarray
import hvplot.pandas
import numpy as np
import os.path
from bokeh.models import HoverTool

from ..data import *

def raster_plot(ps, x_axis, y_axis, vis_axis, selection, vis_path):
    '''
    Create raster plot y_axis vs x_axis for vis axis in ddi.
        ps (processing_set): xradio processing set (dict of msv4 xarray Datasets)
        x_axis (str): x-axis to plot
        y_axis (str): y-axis to plot
        vis_axis (str): visibility component to plot (amp, phase, real, imag)
        selection (dict): select ddi, field, intent, time/baseline/channel/correlation
        vis_path (str): path to visibility file
    Returns: plot
    '''
    # Apply metadata selection to processing set
    do_select_ddi = 'ddi' not in [x_axis, y_axis]
    plot_ps, selection = select_ps(ps, selection, do_select_ddi)
    plot_xds = concat_ps_xds(plot_ps)

    # Check x and y axes, vis axis, and plot selection
    x_axis, y_axis = _check_axes(plot_xds, x_axis, y_axis)
    vis_axis = _check_vis_axis(plot_xds, vis_axis)
    selection = _check_plot_selection(plot_xds, x_axis, y_axis, selection)

    # Calculate complex component
    plot_xds['VISIBILITY'] = get_axis_data(plot_xds, vis_axis)

    # Calculate colorbar limits for amplitudes
    if 'amp' in vis_axis:
        color_limits = _raster_color_limits(plot_xds, vis_axis)

    # Sort xds
    plot_xds = plot_xds.sortby('time')

    # Select plane of unplotted axes
    vis_dims = plot_xds.VISIBILITY.dims # fewer dims after selection
    plot_xds = _select_raster_plane(plot_xds, x_axis, y_axis, selection)

    # Set string for axis unit, convert to GHz if Hz (other axes do not have unit)
    set_frequency_unit(plot_xds)

    # Title and axes for plot
    title = _get_plot_title(plot_xds, (x_axis, y_axis), selection, vis_dims, os.path.basename(vis_path))
    x_axis_labels = get_axis_labels(plot_xds, x_axis)
    y_axis_labels = get_axis_labels(plot_xds, y_axis)
    c_axis_labels = get_vis_axis_labels(plot_xds.VISIBILITY, vis_axis)

    # Combine unflagged and flagged plots in layout
    unflagged_xda = plot_xds.VISIBILITY.where(plot_xds.FLAG == 0.0).rename(c_axis_labels[0])
    layout = _create_plot(unflagged_xda, title, x_axis_labels, y_axis_labels, c_axis_labels, color_limits)

    flagged_xda = plot_xds.VISIBILITY.where(plot_xds.FLAG == 1.0).rename(c_axis_labels[0])
    if np.isfinite(flagged_xda.values).any():
        flagged_plot = _create_plot(flagged_xda, title, x_axis_labels, y_axis_labels, c_axis_labels, color_limits, True)
        layout = layout * flagged_plot if layout is not None else flagged_plot
    return layout

def _check_axes(xds, x_axis, y_axis):
    '''
    Check plot axes are dimensions of visibility data.
    Return renamed axes or throw exception.
    '''
    # Check x and y axes
    x_axis = 'baseline_id' if x_axis == 'baseline' else x_axis
    y_axis = 'baseline_id' if y_axis == 'baseline' else y_axis
    valid_axes = list(xds.VISIBILITY.dims)
    valid_axes.append('ddi')
    if x_axis not in valid_axes or y_axis not in valid_axes:
        raise RuntimeError(f"Invalid x or y axis, please select from {valid_axes}")
    return x_axis, y_axis

def _check_vis_axis(xds, vis_axis):
    ''' Check valid vis axis string. Use visibility data if requested type does not exist. '''
    #TODO: model data, single dish float data ???
    # Check value
    vis_axes = [
        'amp', 'phase', 'real', 'imag',
        'amp_corrected', 'phase_corrected', 'real_corrected', 'imag_corrected'
    ]
    if vis_axis not in vis_axes:
        raise RuntimeError(f"Invalid vis axis. Select from {vis_axes}")

    # Check type
    if 'corrected' in vis_axis and 'VISIBILITY_CORRECTED' not in xds.data_vars.keys():
        print(f"No corrected data, using visibility data.")
        vis_axis = vis_axis.split('_')[0]
    return vis_axis

def _check_plot_selection(xds, x_axis, y_axis, selection):
    ''' Check if plot selection is valid (ignoring invalid keys).
        Returns: validated selection if no exception. '''
    if not selection:
        return

    if 'baseline' in selection.keys():
        selection['baseline_id'] = selection.pop('baseline')

    # Check selection keys: data dimensions and metadata.  Ignore invalid keys.
    plot_keys = list(xds.VISIBILITY.dims)
    metadata_keys = ['ddi', 'field', 'intent']
    invalid_keys = []
    plot_selection = {}
    for key in selection:
        if key not in plot_keys and key not in metadata_keys:
            invalid_keys.append(key)
        elif key in plot_keys:
            plot_selection[key] = selection[key]
    if invalid_keys:
        print(f"Ignoring invalid selection keys: {invalid_keys}.")

    # Test plot selection
    _select_raster_plane(xds, x_axis, y_axis, plot_selection, test=True)
    return selection

def _raster_color_limits(xds, vis_axis):
    ''' Calculate data color scaling ranges to amplitude min/max or 3-sigma limits '''
    if vis_axis != "amp":
        return (None, None)

    print("Calculating colorbar limits for amplitude...")
    # Use unflagged cross correlation data for limits
    xda = xds.VISIBILITY.where(np.logical_not(xds.FLAG).compute(), drop=True)
    if xda.size == 0:
        print("No unflagged data, will autoscale color limits")
        return (None, None)

    # Use cross correlation data for limits (unless all auto-corr)
    xda_cross = xda.where((xds.baseline_antenna1_id != xds.baseline_antenna2_id).compute(), drop=True)
    if xda_cross.size == 0:
        xda_cross = xda

    #with Profiler() as prof, ResourceProfiler() as rprof, CacheProfiler() as cprof:
    minval, maxval, mean, std = dask.compute(
        xda_cross.min(),
        xda_cross.max(),
        xda_cross.mean(),
        xda_cross.std()
    )
    #visualize([prof, rprof, cprof])

    datamin = min(0.0, minval.values)
    clipmin = max(datamin, mean.values - (3.0 * std.values))
    datamax = max(0.0, maxval.values)
    clipmax = min(datamax, mean.values + (3.0 * std.values))
    print(f"Setting colorbar limits ({clipmin:.4f}, {clipmax:.4f})")
    return (clipmin, clipmax)

def _get_non_plot_axes(xds, x_axis, y_axis):
    ''' Return dimensions which are not plot axes '''
    vis_axes = list(xds.VISIBILITY.dims)
    vis_axes.remove(x_axis)
    vis_axes.remove(y_axis)
    return vis_axes
    
def _select_raster_plane(xds, x_axis, y_axis, selection, test=False):
    ''' Select first index of unplotted dimensions if not selected.
        Return selected xds if no exception. '''
    non_plot_axes = _get_non_plot_axes(xds, x_axis, y_axis)
    data_selection = {}
    data_iselection = {}

    for axis in non_plot_axes:
        if selection and axis in selection.keys():
            value = selection[axis]
            if isinstance(value, int):
                data_iselection[axis] = value
            elif isinstance(value, str):
                data_selection[axis] = value
        else:
            data_iselection[axis] = 0 # default first
            selection[axis] = 0

    error = None
    if data_iselection:
        if not test:
            print("Plot selection by index:", data_iselection)
        try:
            xds = xds.isel(data_iselection)
        except IndexError as e:
            raise RuntimeError(f"Plot selection failed: {data_iselection}") from e
    if not error and data_selection:
        try:
            xds = xds.sel(data_selection)
            if not test:
                print("Plot selection by value:", data_selection)
        except KeyError as e:
            raise RuntimeError(f"Plot selection failed: {data_selection}") from e

    if not test:
        return xds

def _get_plot_title(xds, plot_axes, selection, vis_dims, vis_name):
    ''' Form string containing vis name and selected values '''
    title = f"{vis_name}\n"

    # Add plot selection
    if selection is not None:
        if 'field' in selection.keys():
            field = selection['field']
            if isinstance(field, int):
                title += f"field={xds.VISIBILITY.attrs['field_info']['name']} ({field}) "
            else:
                title += f"field={field} "
        if 'intent' in selection.keys():
            title += f"intent={selection['intent']}"
        title += "\n"

    # Add selected dimensions to title: name and index
    for dim in vis_dims:
        if dim not in plot_axes and xds.coords[dim].size == 1:
            label = get_coordinate_labels(xds, dim)
            if dim == 'baseline_id':
                title += f"baseline={label} ({selection[dim]}) "
            elif dim == 'ddi':
                title += f"{dim}={label} " # label is index
            elif dim == 'frequency':
                title += f"{dim}={label} (ch {selection[dim]}) "
            else:
                title += f"{dim}={label} ({selection[dim]}) "
    return title

def _create_plot(xda, title, x_axis_labels, y_axis_labels, c_axis_labels, color_limits, is_flagged = False):
    # create holoviews.element.raster.Image
    x_axis, x_label, x_ticks = x_axis_labels
    y_axis, y_label, y_ticks = y_axis_labels
    c_axis, c_label = c_axis_labels

    # Colormap for vis axis
    colormap = "Viridis" # "Plasma" "Magma"
    cb_position = "left"
    if is_flagged:
        colormap = "kr" # black to reds, "kb" blues
        clabel = "Flagged " + c_label
        cb_position = "right"
        color_limits = None

    # Labels for hover
    xda[x_axis] = xda[x_axis].assign_attrs(long_name=x_axis.upper())
    xda[y_axis] = xda[y_axis].assign_attrs(long_name=y_axis.upper())

    if xda.coords[x_axis].size > 1 and xda.coords[y_axis].size > 1:
        # Raster 2D data
        return xda.hvplot.image(x=x_axis, y=y_axis, width=900, height=600,
            clim=color_limits, cmap=colormap, clabel=c_label,
            title=title, xlabel=x_label, ylabel=y_label,
            rot=90, xticks=x_ticks, yticks=y_ticks,
        ).opts(colorbar_position=cb_position)
    else:
        # Cannot raster 1D data, use scatter
        df = xda.to_dataframe().reset_index() # convert x and y axis from index to column
        return df.hvplot.scatter(
            x=x_axis, y=y_axis, c=c_axis, width=900, height=600,
            clim=color_limits, cmap=colormap, clabel=c_label,
            title=title, xlabel=x_label, ylabel=y_label,
            xticks=x_ticks, yticks=y_ticks, marker='s', hover_cols='all'
        )
