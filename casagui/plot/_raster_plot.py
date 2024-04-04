'''
Functions to create a raster plot of visibilities from xradio processing_set
'''

import dask
import hvplot.xarray
import numpy as np
import os.path

from ..data import *

def raster_plot(ps, ddi, x_axis, y_axis, vis_axis, vis_path):
    '''
    Create raster plot y_axis vs x_axis for vis axis in ddi.
        ps (processing_set): xradio processing set (dict of msv4 xarray Datasets)
        ddi (int): ddi to plot
        x_axis (str): x-axis to plot
        y_axis (str): y-axis to plot
        vis_axis (str): visibility component to plot (amp, phase, real, imag)
        vis_path (str): path to visibility file
    Returns: plot
    '''
    vis_axes = ['amp', 'phase', 'real', 'imag']
    if vis_axis not in vis_axes:
        raise RuntimeError(f"Invalid vis axis, please select from {vis_axes}")

    axis_to_coord = {'baseline': 'baseline_id', 'correlation': 'polarization'}
    if x_axis in axis_to_coord.keys():
        x_axis = axis_to_coord[x_axis]
    if y_axis in axis_to_coord.keys():
        y_axis = axis_to_coord[y_axis]

    # processing set for plot ddi only, concat into a single xarray Dataset
    ddi_ps = get_ddi_ps(ps, ddi)
    plot_xds = concat_ps_xds(ddi_ps)

    # Check plot axes are dimensions of visibility data
    vis_dims = plot_xds.VISIBILITY.dims
    if x_axis not in vis_dims or y_axis not in vis_dims:
        raise RuntimeError(f"Invalid axis, please select from {vis_dims}")

    # Calculate complex component
    plot_xds['VISIBILITY'] = get_axis_data(plot_xds, vis_axis)

    # Calculate colorbar limits for amplitudes
    color_limits = _raster_color_limits(plot_xds, vis_axis)

    # Select first plane of unplotted axes and sort
    plot_xds = plot_xds.sortby('time')
    plot_xds = _select_raster_plane_xds(plot_xds, x_axis, y_axis)

    # Set string for axis unit, convert to GHz if Hz
    set_frequency_unit(plot_xds)

    # Title and axes for plot
    title = _get_plot_title(plot_xds, vis_dims, os.path.basename(vis_path))
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
    print(f"Setting colorbar limits ({clipmin}, {clipmax})")
    return (clipmin, clipmax)

def _select_raster_plane_xds(xds, xaxis, yaxis):
    ''' Select first index of unplotted axes '''
    plot_axes = list(xds.VISIBILITY.dims)
    plot_axes.remove(xaxis)
    plot_axes.remove(yaxis)
    data_selection = {}
    for axis in plot_axes:
        data_selection[axis] = 0
    return xds.isel(data_selection)

def _get_plot_title(xds, vis_dims, vis_name):
    # Return string containing vis name and selected dimension values
    title = f"{vis_name}\nddi={xds.attrs['ddi']}"
    for dim in vis_dims:
        if xds.coords[dim].size == 1:
            # Add selected dimension to title
            label = get_coordinate_labels(xds, dim)
            if dim == 'baseline_id':
                title += f" baseline={label}"
            else:
                title += f" {dim}={label}"
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
