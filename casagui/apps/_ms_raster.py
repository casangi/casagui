'''
Implementation of the ``MsRaster`` application for measurement set raster plotting and editing
'''

import time

import numpy as np

from casagui.plot import MsPlot
from casagui.plot._raster_plot_inputs import check_inputs
from casagui.plot._raster_plot import RasterPlot

class MsRaster(MsPlot):
    '''
    Plot MeasurementSet data as raster plot.

    Args:
        ms (str): path to MSv2 (.ms) or MSv4 (.zarr) file.
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
        self._raster_plot = RasterPlot()
        self._spw_color_limits = {} # store calculated color limits

        if interactive:
            # Set defaults
            self._plot()
            self._launch_gui()

    def set_ms(self, ms):
        ''' Set MS path for current MsRaster '''
        ms_changed = super().set_ms(ms)
        if ms_changed:
            self._raster_plot.reset_xds_plot_params()
            self._spw_color_limits = {}
        return ms_changed

    def set_style_params(self, unflagged_cmap='viridis', flagged_cmap='reds', show_colorbar=True):
        '''
            Set styling parameters for the plot, such as colormaps and whether to show colorbar.
            Placeholder for future styling such as fonts.

            Args:
                unflagged_cmap (str): colormap to use for unflagged data.
                flagged_cmap (str): colormap to use for flagged data.
                show_colorbar (bool): Whether to show colorbar with plot.  Default True.
        '''
        self._raster_plot.set_style_params(unflagged_cmap, flagged_cmap, show_colorbar)

# pylint: disable=too-many-arguments, too-many-positional-arguments, too-many-locals, unused-argument
    def plot(self, x_axis='baseline', y_axis='time', vis_axis='amp', selection=None, aggregator=None, agg_axis=None,
             iter_axis= None, iter_range=None, subplots=None, color_limits=None, title=None, clear_plots=True):
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
            iter_range (tuple): (start, end) inclusive index values for iteration plots.
                Default (0, 0) (first iteration only). Use (0, -1) for all iterations.
                If subplots is a grid, the range is limited by the grid size.
                If subplots is a single plot, all iteration plots in the range can be saved using export_range in save().
            subplots (None, tuple): set a grid of (rows, columns).  None = (1, 1) for single plot.
                Use with iter_axis and iter_range, or clear_plots=False.
                If used in multiple calls, the last subplots tuple will be used to determine grid to show or save.
            color_limits (tuple): (min, max) of colorbar.  Default None is to autoscale.
                When color_limits=None and vis_axis='amp', limits will be computed from statistics.
            title (str): Plot title, default None (generate title from ms and selection).
            clear_plots (bool): whether to clear list of plots.

        If not interactive and plotting is successful, use show() or save() to view/save the plot only.
        '''
        start = time.time()

        inputs = locals() # collect arguments into dict (not unused as pylint complains!)

        # Clear for new plot
        self._reset_plot(inputs['clear_plots'])

        # Validate input arguments
        inputs['data_dims'] = self._ms_info['data_dims'] # needed to check axis values and rename dimensions
        check_inputs(inputs)
        self._plot_inputs = inputs

        # Do plot if valid MS is set
        if self._data and self._data.is_valid():
            if self._plot_inputs['selection']:
                # Preserve user selection dict; plot selection will be modified for plot
                self._plot_inputs['selection'] = self._plot_inputs['selection'].copy()

            if self._interactive:
                self._update_gui() # triggers plot
            else:
                if self._plot_inputs['iter_axis']:
                    self._do_iter_plot(self._plot_inputs)
                else:
                    plot, _ = self._do_plot(self._plot_inputs)
                    self._plots.append(plot)
        else:
            self._logger.warning("Plot inputs set but cannot plot: input MS path is invalid or missing.")
        self._logger.debug("Plot elapsed time: %.2fs.", time.time() - start)
# pylint: enable=too-many-arguments, too-many-positional-arguments, too-many-locals, unused-argument

    def save(self, filename='', fmt='auto', export_range='one'):
        '''
        Save plot to file.

        Args:
            filename (str): Name of file to save. Default '': see below.
            fmt (str): Format of file to save ('png', 'svg', 'html', or 'gif'). Default 'auto': inferred from filename.
            export_range(str): 'one' or 'all' for iteration plots when subplots is a single-plot grid. Ignored otherwise. 

        If filename is set and fmt='auto', the plot will be exported in the format of the filename extension.
        If filename is not set, the plot will be saved as a PNG with name {vis}_raster.{ext}.
        When exporting 'all' iteration plots, the plot index will be appended to the filename: {filename}_{index}.{ext}.
        '''
        if not filename:
            filename = f"{self._ms_info['basename']}_raster.png"
        super().save(filename, fmt, export_range)

    def _do_plot(self, plot_inputs):
        ''' Create plot using plot inputs '''
        plot = None
        plot_params = {}

        if not self._plot_init:
            self._init_plot(plot_inputs)

        try:
            # Select vis_axis data to plot and update selection; returns xarray Dataset
            raster_data = self._data.get_raster_data(plot_inputs)
        except RuntimeError as e:
            error = f"Plot data failed: {str(e)}"
            super()._notify(error, "error", 0)
            return plot, plot_params


        # Get params needed for plot, such as title, labels, and ticks
        plot_inputs['color_limits'] = self._get_color_limits(plot_inputs)
        plot_inputs['ms_name'] = self._ms_info['basename'] # for title
        self._raster_plot.set_data_params(raster_data, plot_inputs)

        # Make plot
        try:
            plot, colorbar_params = self._raster_plot.raster_plot(raster_data, self._logger)
        except RuntimeError as e:
            error = f"Plot failed: {str(e)}"
            super()._notify(error, "error", 0)
        return plot, colorbar_params

    def _do_iter_plot(self, plot_inputs):
        ''' Create one plot per iteration value in iter_range which fits into subplots '''
        # Default (0, 0) (first iteration only). Use (0, -1) for all iterations.
        # If subplots is a grid, end iteration index is limited by the grid size.
        # If subplots is a single plot, all iteration plots in the range can be saved using export_range in save().
        iter_axis = plot_inputs['iter_axis']
        iter_range = plot_inputs['iter_range']
        subplots = plot_inputs['subplots']

        iter_range = (0, 0) if iter_range is None else iter_range
        start_idx, end_idx = iter_range

        iter_values = self._data.get_dimension_values(iter_axis)
        n_iter = len(iter_values)

        if start_idx >= n_iter:
            raise IndexError(f"iter_range start {start_idx} is greater than number of iterations {n_iter}")
        end_idx = n_iter if (end_idx == -1 or end_idx >= n_iter) else end_idx + 1
        num_iter_plots = end_idx - start_idx

        # Plot the minimum number of plots in iter range or subplots grid
        num_subplots = np.prod(subplots) if subplots else 1
        num_iter_plots = min(end_idx - start_idx, num_subplots) if num_subplots > 1 else num_iter_plots
        end_idx = start_idx + num_iter_plots

        # Init plot before selecting iter values
        self._init_plot(plot_inputs)

        for i in range(start_idx, end_idx):
            # Select iteration value and make plot
            value = iter_values[i]
            self._logger.info("Plot %s iteration value %s", iter_axis, value)
            plot_inputs['selection'][iter_axis] = value
            plot, _ = self._do_plot(plot_inputs)
            self._plots.append(plot)

    def _init_plot(self, plot_inputs):
        ''' Apply selection and set colorbar limits '''
        # Apply user + data_group selection, then select first spw
        # Set data group and name of its correlated data
        self._set_data_group(plot_inputs)

        # Do selection and add spw
        self._data.select_data(plot_inputs['selection'])
        self._select_first_spw(plot_inputs)
        self._plot_init = True

        # Print data info for spw selection
        self._logger.info("Plotting %s msv4 datasets.", self._data.get_num_ms())
        self._logger.info("Maximum dimensions for selected spw: %s", self._data.get_max_data_dims())

    def _select_first_spw(self, plot_inputs):
        ''' Determine first spw if not in user selection '''
        if 'spw_name' not in plot_inputs['selection']:
            first_spw = self._data.get_first_spw()
            self._data.select_data({'spw_name': first_spw})
            plot_inputs['selection']['spw_name'] = first_spw

    def _get_color_limits(self, plot_inputs):
        ''' Calculate stats for color limits for non-interactive amplitude plots. '''
        color_limits = None
        if 'color_limits' in plot_inputs and plot_inputs['color_limits'] is not None:
            return plot_inputs['color_limits']

        if plot_inputs['vis_axis']=='amp' and not plot_inputs['aggregator']:
            # For amplitude, limit colorbar range using ms stats
            spw_name = plot_inputs['selection']['spw_name']
            if spw_name in self._spw_color_limits:
                color_limits = self._spw_color_limits[spw_name]
            else:
                # Select spw name and data group only
                spw_data_selection = {'spw_name': spw_name, 'data_group': plot_inputs['selection']['data_group']}
                color_limits = self._calc_amp_color_limits(spw_data_selection)
                self._spw_color_limits[spw_name] = color_limits

        if color_limits:
            self._logger.info("Setting colorbar limits: (%.4f, %.4f).", color_limits[0], color_limits[1])
        else:
            self._logger.info("Autoscale colorbar limits")
        return color_limits

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
        self._logger.debug("Stats elapsed time: %.2fs.", time.time() - start)
        return color_limits

    def _reset_plot(self, clear_plots=True):
        ''' Reset any plot settings for a new plot '''
        # Clear plot list
        if clear_plots:
            super().clear_plots()

        # Reset selection in data
        super().clear_selection()

        # Reset data-related plot params
        self._raster_plot.reset_data_params()

        self._plot_init = False

    def _set_data_group(self, plot_inputs):
        ''' Add base data_group to plot inputs selection if not in user selection '''
        if 'selection' not in plot_inputs or not plot_inputs['selection']:
            plot_inputs['selection'] = {}
        if 'data_group' not in plot_inputs['selection']:
            plot_inputs['selection']['data_group'] = 'base'
        if self._data and self._data.is_valid():
            plot_inputs['correlated_data'] = self._data.get_correlated_data(plot_inputs['selection']['data_group'])

    def _launch_gui(self):
        pass
