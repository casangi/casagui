'''
Implementation of the ``MsRaster`` application for measurement set raster plotting and editing
'''

import os
import time

from casagui.plot._ms_plot import MsPlot
from casagui.data.measurement_set._xds_data import VIS_AXIS_OPTIONS
from casagui.data.measurement_set._raster_data import AGGREGATOR_OPTIONS
from casagui.plot._xds_raster_plot import raster_plot_params, raster_plot

class MsRaster(MsPlot):
    '''
    Plot MeasurementSet data as raster plot.

    Args:
        ms (str): path in MSv2 (.ms) or MSv4 (.zarr) format.
        log_level (str): logging threshold'. Options include "debug", "info", "warning", "error", "critical". Default "info".
        interactive (bool): whether to launch interactive GUI in browser. Default False.

    Example:
        from casagui.plots import MsRaster
        msr = MsRaster(ms='myvis.ms')
        msr.summary()
        msr.plot(x_axis='frequency', y_axis='time', vis_axis='amp', data_group='base')
        msr.show()
        msr.save() # saves as {ms name}_raster.png
    '''

    def __init__(self, ms=None, log_level="info", interactive=False):
        super().__init__(ms, log_level, interactive, "MsRaster")
        self._spw_color_limits = {}

        if interactive:
            self._set_default_plot_inputs() # should include all plot() parameters as well as color_limits
            self._launch_gui()

    def plot(self, x_axis='baseline', y_axis='time', vis_axis='amp', selection=None, aggregator=None, agg_axis=None, iter_axis= None, title=None, clear_plots=True):
        '''
        Create a raster plot of vis_axis data in the data_group after applying selection.
        Plot axes include data dimensions (time, baseline/antenna, frequency, polarization).
        Dimensions not set as plot axes can be selected, else the first value will be used, unless aggregated.

        Args:
            x_axis (str): Plot x-axis. Default 'baseline' ('antenna_name' for spectrum data).
            y_axis (str): Plot y-axis. Default 'time'.
            vis_axis (str): Complex visibility component to plot (amp, phase, real, imag). Default 'amp'.
                Call data_groups() to see options.
            selection (dict): selected data to plot. Options include:
                Processing Set selection: by summary column names. Call summary() to see options.
                    'query': for pandas query of summary() columns.
                    Default: select first spw (by id).
                MeasurementSetXds selection:
                    Name for correlated data, flags, weights, and uvw: 'data_group'. Default value 'base'.
                        Use data_groups() to get data group names.
                    Dimensions:
                        Visibility dimensions: 'baseline' 'time', 'frequency', 'polarization'
                        Spectrum dimensions: 'antenna_name', 'time', 'frequency', 'polarization'
                        Default value is index 0 (after user selection) for non-axis dimensions unless aggregated.
                        Use antennas() to get antenna names. Select 'baseline' as "<name1> & <name2>".
                        Use summary() to list frequencies and polarizations.
                        TODO: how to select time?
            aggregator (str): reduction for rasterization. Default None.
                Options include 'max', 'mean', 'min', 'std', 'sum', 'var'.
            agg_axis (str, list): which dimension to apply aggregator across. Default None.
                Options include one or more dimensions.
                If agg_axis is None and aggregator is set, aggregates over all non-axis dimensions.
                If one agg_axis is selected, the non-agg dimension will be selected.
            iter_axis (str): dimension over which to iterate values (starting at layout start).
            title (str): Plot title, default None (generate title from ms and selection).
            clear_plots (bool): whether to clear list of plots.

        If not interactive and plotting is successful, use show() or save() to view/save the plot only.
        '''
        start = time.time()

        # Validate input arguments
        if not self._data.is_valid():
            raise RuntimeError("Input MS path is invalid or missing, cannot plot")

        # Clear for new plot
        super().clear_selection() # in MsData
        if clear_plots:
            super().clear_plots()

        # Check input values and save ms basename
        self._check_plot_inputs(x_axis, y_axis, vis_axis, selection, aggregator, agg_axis, iter_axis, title)
        self._plot_inputs['ms_basename'] = self._basename

        # Select default data group if not in user selection
        self._select_data_group()

        # Apply user + data_group selection
        self._data.select_data(self._plot_inputs['selection'])

        # Determine first spw if not in user selection
        if 'spw_name' not in self._plot_inputs['selection']:
            first_spw = self._data.get_first_spw()
            self._plot_inputs['selection']['spw_name'] = first_spw
            self._data.select_data({'spw_name': first_spw})

        self._logger.info(f"Plotting {self._data.get_num_ms()} msv4 datasets.")
        self._logger.info(f"Maximum dimensions for selected spw: {self._data.get_max_data_dims()}")

        # Set colorbar limits for amp vis axis if not interactive (user can adjust interactively)
        self._set_color_limits()

        if self._plot_inputs['iter_axis']:
            self._do_iter_plot()
        else:
            self._do_plot()

        self._logger.debug(f"Plot elapsed time: {time.time() - start:.2f}s.")

    def show(self, title=None, port=0, layout=None):
        ''' 
        Show interactive Bokeh plots in a browser. Plot tools include pan, zoom, hover, and save.
        Multiple plots can be shown in a panel layout.  Default is to show the first plot only.
            title (str): browser tab title.  Default is "MsRaster {ms_name}".
            port (int): optional port number to use.  Default 0 will select a port number.

            Options for showing multiple plots (iteration or clearplots=False):
            layout (tuple): (start, rows, columns) options for saving multiple plots in grid. Default None (single plot).
        '''
        super().show(title, port, layout)

    def save(self, filename='', fmt='auto', layout=None, export_range='one'):
        '''
        Save plot to file.
            filename (str): Name of file to save. Default '': see below.
            fmt (str): Format of file to save ('png', 'svg', 'html', or 'gif'). Default 'auto': inferred from filename.

            Options for saving multiple plots (iteration or clearplots=False):
            layout (tuple): (start, rows, columns) for saving multiple plots in grid or selecting start plot. Default None is single plot (0,1,1).
            export_range(str): when layout is single plot, whether to save start plot only ('one') or all plots starting at start plot ('all'). Ignored if layout is a grid.

        If filename is set, the plot will be exported to the specified filename in the format of its extension (see fmt options).  If not set, the plot will be saved as a PNG with name {vis}_raster.{ext}.
        When exporting multiple plots as single plots, the plot index will be appended to the filename {filename}_{index}.{ext}.
        '''
        if not filename:
            filename = f"{self._plot_inputs['ms_basename']}_raster.png"
        super().save(filename, fmt, layout, export_range)

    def _select_data_group(self):
        ''' Add default data group to selection if not set by user. Set correlated_data in plot inputs. '''
        selection = self._plot_inputs['selection']
        if not selection:
            selection = {}
        if 'data_group' not in selection:
            selection['data_group'] = 'base'

        self._plot_inputs['selection'] = selection
        self._plot_inputs['correlated_data'] = self._data.get_correlated_data(selection['data_group'])

    def _check_plot_inputs(self, x_axis, y_axis, vis_axis, selection, aggregator, agg_axis, iter_axis, title):
        ''' Check plot parameters against Processing Set.  Set data group selection if user did not. '''
        plot_inputs = {}

        # Rename "baseline" x_axis or y_axis for SPECTRUM data dimension
        data_dims = self._data.get_data_dimensions()
        x_axis = 'antenna_name' if x_axis == 'baseline' and "antenna_name" in data_dims else x_axis
        y_axis = 'antenna_name' if y_axis == 'baseline' and "antenna_name" in data_dims else y_axis

        if x_axis not in data_dims or y_axis not in data_dims:
            raise ValueError(f"Invalid parameter value: select x and y axis from {data_dims}.")
        plot_inputs['data_dims'] = data_dims
        plot_inputs['x_axis'] = x_axis
        plot_inputs['y_axis'] = y_axis

        if vis_axis not in VIS_AXIS_OPTIONS:
            raise ValueError(f"Invalid parameter value: vis_axis {vis_axis}. Options include {VIS_AXIS_OPTIONS}")
        plot_inputs['vis_axis'] = vis_axis

        if selection:
            if not isinstance(selection, dict):
                 raise RuntimeError("Invalid parameter type: selection must be dictionary.")

            if 'data_group' in selection and selection['data_group'] not in self._data.get_data_groups():
                raise ValueError(f"Invalid parameter value: data_group {data_group}. Use data_groups() to see options.")

            # Save a copy so that automatic selections do not change user's selection
            plot_inputs['selection'] = selection.copy()
        else:
            plot_inputs['selection'] = selection

        if aggregator and aggregator not in AGGREGATOR_OPTIONS:
            raise RuntimeError(f"Invalid parameter value: aggregator {aggregator}. Options include {AGGREGATOR_OPTIONS}.")
        plot_inputs['aggregator'] = aggregator

        # Set agg_axis to non-plotted dim axes if not set
        if aggregator and not agg_axis:
            agg_axis = data_dims
            agg_axis.remove(x_axis)
            agg_axis.remove(y_axis)

        if agg_axis:
            if not isinstance(agg_axis, list) and not isinstance(agg_axis, str):
                raise RuntimeError(f"Invalid parameter value: agg axis {agg_axis}. Options include one or more dimensions {data_dims}.")
            if isinstance(agg_axis, str):
                agg_axis = [agg_axis]
            for axis in agg_axis:
                if axis not in data_dims or axis in (x_axis, y_axis):
                    raise RuntimeError(f"Invalid parameter value: aggregator axis {axis}. Must be dimension which is not a plot axis.")
        plot_inputs['agg_axis'] = agg_axis

        if iter_axis and (iter_axis not in data_dims or iter_axis in (x_axis, y_axis)):
            raise RuntimeError(f"Invalid parameter value: iteration axis {iter_axis}. Must be dimension which is not a plot axis.")
        plot_inputs['iter_axis'] = iter_axis

        if title and not isinstance(title, str):
            raise RuntimeError(f"Invalid parameter type: title must be a string.")
        plot_inputs['title'] = title
        self._plot_inputs = plot_inputs

    def _set_color_limits(self):
        ''' Calculate stats for color limits for non-interactive amplitude plots. '''
        color_limits = None
        if not self._interactive and self._plot_inputs['vis_axis']=='amp' and not self._plot_inputs['aggregator']:
            # For amplitude, limit colorbar range using ms stats
            spw_name = self._plot_inputs['selection']['spw_name']
            if spw_name in self._spw_color_limits:
                color_limits = self._spw_color_limits[spw_name]
            else:
                # Select spw name and data group only
                spw_data_selection = {'spw_name': spw_name, 'data_group': self._plot_inputs['selection']['data_group']}
                color_limits = self._calc_amp_color_limits(spw_data_selection)
                self._spw_color_limits[spw_name] = color_limits

        if color_limits:
            self._logger.info(f"Setting colorbar limits: ({color_limits[0]:.4f}, {color_limits[1]:.4f}).")
        else:
            self._logger.info("Autoscale colorbar limits")

        self._plot_inputs['color_limits'] = color_limits

    def _calc_amp_color_limits(self, selection):
        # Calculate colorbar limits from amplitude stats for unflagged data in selected spw
        self._logger.info("Calculating stats for colorbar limits.")
        start = time.time()

        ms_stats = self._data.get_vis_stats(selection, 'amp')
        if not ms_stats:
            return None # autoscale

        min_val, max_val, mean, std = ms_stats

        data_min = min(0.0, min_val)
        clip_min = max(data_min, mean - (3.0 * std))
        data_max = max(0.0, max_val)
        clip_max = min(data_max, mean + (3.0 * std))

        if clip_min == 0.0 and clip_max == 0.0:
            color_limits = None # flagged data only
        else:
            color_limits = (clip_min, clip_max)
        self._logger.debug(f"Stats elapsed time: {time.time() - start:.2f} s.")
        return color_limits

    def _do_plot(self):
        ''' Create plot using plot inputs and add to list '''
        # Select data to plot and update selection; returns xarray Dataset
        raster_data, selection = self._data.get_raster_data(self._plot_inputs)
        self._plot_inputs['selection'] = selection

        if raster_data:
            # Get options needed for plot
            plot_params = raster_plot_params(raster_data, self._plot_inputs)
            plot = raster_plot(raster_data, plot_params)

            if plot is None:
                raise RuntimeError("Plot failed.")

            if self._interactive:
                pass # TODO: update gui
            else:
                self._plots.append(plot)

    def _do_iter_plot(self):
        ''' Create one plot per iteration value '''
        iter_axis = self._plot_inputs['iter_axis']
        iter_values = self._data.get_dimension_values(iter_axis)
        if iter_values:
            for value in iter_values:
                # Select iteration value and make plot
                self._logger.info(f"Plot {iter_axis} iteration value {value}")
                self._plot_inputs['selection'][iter_axis] = value
                self._do_plot()

    def _set_default_plot_inputs(self):
        ''' Default values for plot inputs. Used for interactive gui when plot() is not called. '''
        # include all plot() parameters and color_limits
        self._plot_inputs['x_axis'] = 'baseline'
        self._plot_inputs['y_axis'] = 'time'
        self._plot_inputs['vis_axis'] = 'amp'
        self._plot_inputs['selection'] = {'data_group': 'base'}
        self._plot_inputs['aggregator'] = None
        self._plot_inputs['agg_axis'] = None
        self._plot_inputs['iter_axis'] = None
        self._plot_inputs['title'] = None
        self._plot_inputs['color_limits'] = None

    def _launch_gui(self):
        pass # TODO
