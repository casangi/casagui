'''
Functions to create a raster plot of visibilities from xradio processing_set
'''

import dask
import hvplot.xarray
import numpy as np
import os.path

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
    # Apply metadata selection to processing set, concat into xarray Dataset
    ddi_ps = get_ddi_ps(ps, selection)
    plot_xds = concat_ps_xds(ddi_ps)
    ddi = plot_xds.attrs['ddi']

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

    # Set string for axis unit, convert to GHz if Hz
    set_frequency_unit(plot_xds)

    # Title and axes for plot
    title = _get_plot_title(plot_xds, selection, vis_dims, os.path.basename(vis_path))
    x_axis_labels = get_axis_labels(plot_xds, x_axis)
    y_axis_labels = get_axis_labels(plot_xds, y_axis)
    c_axis_label = get_vis_axis_label(plot_xds.VISIBILITY, vis_axis)

    # Combine unflagged and flagged plots in layout
    print("Creating plot")
    unflagged_xda = plot_xds.VISIBILITY.where(plot_xds.FLAG == 0.0)
    layout = _create_plot(unflagged_xda, title, x_axis_labels, y_axis_labels, c_axis_label, color_limits)

    flagged_xda = plot_xds.VISIBILITY.where(plot_xds.FLAG == 1.0)
    if np.isfinite(flagged_xda.values).any():
        flagged_plot = _create_plot(flagged_xda, title, x_axis_labels, y_axis_labels, c_axis_label, color_limits, True)
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
    vis_dims = xds.VISIBILITY.dims
    if x_axis not in vis_dims or y_axis not in vis_dims:
        raise RuntimeError(f"Invalid x or y axis, please select from {vis_dims}")
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

def _get_non_display_axes(xds, x_axis, y_axis):
    ''' Return dimensions which are not plot axes '''
    vis_axes = list(xds.VISIBILITY.dims)
    vis_axes.remove(x_axis)
    vis_axes.remove(y_axis)
    return vis_axes
    
def _select_raster_plane(xds, x_axis, y_axis, selection, test=False):
    ''' Select first index of unplotted dimensions if not selected.
        Return selected xds if no exception. '''
    non_display_axes = _get_non_display_axes(xds, x_axis, y_axis)
    data_selection = {}
    data_iselection = {}

    for axis in non_display_axes:
        if selection and axis in selection.keys():
            value = selection[axis]
            if isinstance(value, int):
                data_iselection[axis] = value
            elif isinstance(value, str):
                data_selection[axis] = value
        else:
            data_iselection[axis] = 0 # default first

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

def _get_plot_title(xds, selection, vis_dims, vis_name):
    ''' Form string containing vis name and selected values '''
    title = f"{vis_name}\nddi={xds.attrs['ddi']} "

    # Append metadata selection to ddi
    if selection is not None:
        field = selection['field'] if 'field' in selection.keys() else None
        intent = selection['intent'] if 'intent' in selection.keys() else None
        if field:
            if isinstance(field, int):
                field = xds.VISIBILITY.attrs['field_info']['name']
            title += f"field={field} "
        if intent:
            title += f"intent={intent} "

    # Add selected dimensions to title
    for dim in vis_dims:
        if xds.coords[dim].size == 1:
            label = get_coordinate_labels(xds, dim)
            if dim == 'baseline_id':
                title += f"baseline={label} "
            elif dim == 'polarization':
                title += f"polarization={label} "
            else:
                title += f"{dim}={label} "
    return title

def _create_plot(xda, title, x_axis_labels, y_axis_labels, c_axis_label, color_limits, is_flagged = False):
    # create holoviews.element.raster.Image
    x_axis, x_label, x_ticks = x_axis_labels
    y_axis, y_label, y_ticks = y_axis_labels

    # Colormap for vis axis
    colormap = "Viridis" # "Plasma" "Magma"
    clabel = c_axis_label
    cb_position = "left"
    if is_flagged:
        colormap = "kr" # black to reds, "kb" blues
        clabel = "Flagged " + clabel
        cb_position = "right"
        color_limits = None

    return xda.hvplot(x=x_axis, y=y_axis, width=900, height=600,
        clim=color_limits, cmap=colormap, clabel=clabel,
        title=title, xlabel=x_label, ylabel=y_label,
        rot=90, xticks=x_ticks, yticks=y_ticks
    ).opts(colorbar_position=cb_position)
