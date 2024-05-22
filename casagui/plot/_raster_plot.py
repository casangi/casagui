'''
Functions to create a raster plot of visibilities from xradio processing_set
'''

import dask
import hvplot.xarray
import hvplot.pandas
import numpy as np
import os.path
from bokeh.models import HoverTool

from ..data._xds_utils import fix_coordinate_units
from ..data._vis_data import get_axis_data
from ._plot_axes import get_coordinate_label, get_axis_labels, get_vis_axis_labels

def raster_plot(xds, x_axis, y_axis, vis_axis, selection, vis_path, color_limits):
    '''
    Create raster plot y_axis vs x_axis for vis axis in ddi.
        xds (xarray Dataset): concat of msv4 xarray Datasets containing vis data
        x_axis (str): x-axis to plot
        y_axis (str): y-axis to plot
        vis_axis (str): visibility component to plot (amp, phase, real, imag)
        selection (dict): select ddi, field, intent, time/baseline/channel/correlation
        vis_path (str): path to visibility file
        color_limits (tuple): color limits (min, max) for plotting amplitude

    Returns: holoviews Image or Overlay (if flagged data)
    '''
    # Check x and y axes, vis axis
    x_axis, y_axis = _check_axes(xds, x_axis, y_axis)
    vis_axis = _check_vis_axis(xds, vis_axis)

    # xradio sets unit as list not string
    fix_coordinate_units(xds)

    # Calculate complex component
    xds['VISIBILITY'] = get_axis_data(xds, vis_axis)

    # Sort xds
    xds = xds.sortby('time')

    # Get dimensions before selection
    vis_dims = xds.VISIBILITY.dims

    # Check plot selection: exception if fails
    xds = _apply_xds_selection(xds, x_axis, y_axis, selection)

    # Title for plot
    title = _get_plot_title(xds, x_axis, y_axis, vis_dims, selection, os.path.basename(vis_path))

    # Axes for plot (indexed for regular spacing where needed)
    xds, x_axis_labels = get_axis_labels(xds, x_axis)
    xds, y_axis_labels = get_axis_labels(xds, y_axis)
    c_axis_labels = get_vis_axis_labels(xds.VISIBILITY, vis_axis)

    # Plot unflagged data
    unflagged_xda = xds.VISIBILITY.where(xds.FLAG == 0.0).rename(c_axis_labels[0])
    overlay = _create_plot(unflagged_xda, title, x_axis_labels, y_axis_labels, c_axis_labels, color_limits)

    # Overlay flagged data plot
    #flagged_xda = xds.VISIBILITY.where(xds.FLAG == 1.0).rename(c_axis_labels[0])
    #if flagged_xda.count().values > 0:
    #    flagged_plot = _create_plot(flagged_xda, title, x_axis_labels, y_axis_labels, c_axis_labels, color_limits, True)
    #    overlay = overlay * flagged_plot if overlay else flagged_plot

    return overlay

def _check_axes(xds, x_axis, y_axis):
    '''
    Check plot axes are dimensions of visibility data.
    Return renamed axes or raise exception.
    '''
    # Check x and y axes
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

def _apply_xds_selection(xds, x_axis, y_axis, selection):
    ''' Return selected xds if no selection exception. '''
    if selection is None:
        selection = {}

    vis_dims = xds.VISIBILITY.dims
    index_selection = {}
    value_selection = {}
    for dim in vis_dims:
        if dim not in (x_axis, y_axis):
            if dim not in selection.keys():
                selection[dim] = 0

            value = selection[dim]
            if isinstance(value, int):
                index_selection[dim] = value
            elif isinstance(value, str) or isinstance(value, float):
                value_selection[dim] = value
            else:
                print("Ignoring invalid selection:", dim, value)

    if index_selection:
        try:
            xds = xds.isel(index_selection)
        except IndexError as e:
            raise RuntimeError(f"Plot selection failed: {index_selection}") from e
    if value_selection:
        try:
            xds = xds.sel(value_selection)
        except KeyError as e:
            raise RuntimeError(f"Plot selection failed: {value_selection}") from e
    return xds

def _get_plot_title(xds, x_axis, y_axis, vis_dims, selection, vis_name):
    ''' Form string containing vis name and selected values '''
    title = f"{vis_name}\n"

    # Add processing set selection: ddi, field, and intent
    if selection:
        ddi_label = f"ddi={selection['ddi']} " if 'ddi' in selection.keys() else ''
        field_label = ''
        if 'field' in selection.keys():
            field = selection['field']
            field_label = f"field={xds.VISIBILITY.attrs['field_info']['name']} ({field}) " if isinstance(field, int) else f"field={field} "
        intent_label = f"intent={selection['intent']}" if 'intent' in selection.keys() else ''
        if ddi_label or field_label or intent_label:
            title += ddi_label + field_label + intent_label + "\n"

    # Add selected dimensions to title: name and index
    for dim in vis_dims:
        if dim not in (x_axis, y_axis) and xds[dim].size == 1:
            label = get_coordinate_label(xds, dim)
            index = selection[dim] if (selection and dim in selection.keys()) else None

            if dim == 'baseline_id':
                title += f"baseline={label} "
            else:
                title += f"{dim}={label} "

            if isinstance(index, int):
                title += f"({index}) "
    return title

def _create_plot(xda, title, x_axis_labels, y_axis_labels, c_axis_labels, color_limits, is_flagged = False):
    # create holoviews.element.raster.Image
    x_axis, x_label, x_ticks = x_axis_labels
    y_axis, y_label, y_ticks = y_axis_labels
    c_axis, c_label = c_axis_labels

    # Colormap for vis axis
    colormap = "Viridis" # "Plasma" "Magma"
    cb_position = 'left'
    if is_flagged:
        colormap = "kr" # black to reds, "kb" blues
        c_label = "Flagged " + c_label
        cb_position = 'right'

    # Labels for hover
    xda[x_axis] = xda[x_axis].assign_attrs(long_name=x_axis.capitalize())
    xda[y_axis] = xda[y_axis].assign_attrs(long_name=y_axis.capitalize())
    xda['baseline_antenna1_id'] = xda['baseline_antenna1_id'].assign_attrs(long_name='Antenna1_id')
    xda['baseline_antenna2_id'] = xda['baseline_antenna2_id'].assign_attrs(long_name='Antenna2_id')

    if xda.coords[x_axis].size > 1 and xda.coords[y_axis].size > 1:
        # Raster 2D data
        return xda.hvplot(x=x_axis, y=y_axis, c=c_axis, width=900, height=600,
            clim=color_limits, cmap=colormap, clabel=c_label,
            title=title, xlabel=x_label, ylabel=y_label,
            rot=90, xticks=x_ticks, yticks=y_ticks,
            #hover_cols=['baseline_antenna1_id', 'Antenna1_name', 'baseline_antenna2_id', 'Antenna2_name'] # only works with time and baseline axes
        ).opts(colorbar_position=cb_position)
    else:
        # Cannot raster 1D data, use scatter
        df = xda.to_dataframe().reset_index() # convert x and y axis from index to column
        return df.hvplot.scatter(
            x=x_axis, y=y_axis, c=c_axis, width=600, height=600,
            clim=color_limits, cmap=colormap, clabel=c_label,
            title=title, xlabel=x_label, ylabel=y_label,
            xticks=x_ticks, yticks=y_ticks, marker='s'
        )
