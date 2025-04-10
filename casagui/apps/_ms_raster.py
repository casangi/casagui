'''
Implementation of the ``MsRaster`` application for measurement set raster plotting and editing
'''

import time

import holoviews as hv

from casagui.plot import MsPlot
from casagui.plot._raster_plot_inputs import check_inputs
from casagui.plot._xds_raster_plot import raster_plot_params, raster_plot

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
        self._spw_color_limits = {}

        if self._interactive:
            self._logger.warning("Interactive mode is not implemented yet")
            self._interactive = False

# pylint: disable=too-many-arguments, too-many-positional-arguments
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

        # Check valid MS is set
        if not self._data or not self._data.is_valid():
            raise RuntimeError("Input MS path is invalid or missing, cannot plot")

        # Clear for new plot
        self._reset_plot(clear_plots)

        # Validate input arguments
        inputs = {'x_axis': x_axis, 'y_axis': y_axis, 'vis_axis': vis_axis, 'selection': selection,
            'aggregator': aggregator, 'agg_axis': agg_axis, 'iter_axis': iter_axis, 'title': title}
        inputs['data_dims'] = self._ms_info['data_dims'] # needed to check axis values and select dimensions
        check_inputs(inputs)
        self._plot_inputs = inputs

        # Preserve user selection dict; plot selection will be modified for plot
        if self._plot_inputs['selection']:
            self._plot_inputs['selection'] = self._plot_inputs['selection'].copy()

        if self._interactive:
            self._update_gui() # triggers plot
        else:
            if self._plot_inputs['iter_axis']:
                self._do_iter_plot(self._plot_inputs)
            else:
                plot = self._do_plot(self._plot_inputs)
                self._plots.append(plot)
        self._logger.debug("Plot elapsed time: %.2fs.", time.time() - start)
# pylint: enable=too-many-arguments, too-many-positional-arguments

    def save(self, filename='', fmt='auto', layout=None, export_range='one'):
        '''
        Save plot to file.
            filename (str): Name of file to save. Default '': see below.
            fmt (str): Format of file to save ('png', 'svg', 'html', or 'gif'). Default 'auto': inferred from filename.

            Options for saving multiple plots (iteration or clearplots=False):
            layout (tuple): (start, rows, columns) for saving multiple plots in grid or selecting start plot. Default None is single plot (0,1,1).
            export_range(str): when layout is single plot, whether to save start plot only ('one') or all plots starting at start plot ('all'). Ignored if layout is a grid.

        filename:
            If set, the plot will be exported to the specified filename in the format of its extension (see fmt options).
            If not set, the plot will be saved as a PNG with name {vis}_raster.{ext}.
            When exporting multiple plots as single plots, the plot index will be appended to the filename {filename}_{index}.{ext}.
        '''
        if not filename:
            filename = f"{self._ms_info['basename']}_raster.png"
        super().save(filename, fmt, layout, export_range)

    def _do_plot(self, plot_inputs):
        ''' Create plot using plot inputs '''
        plot = None

        if not self._plot_init:
            self._init_plot(plot_inputs)

        try:
            # Select vis_axis data to plot and update selection; returns xarray Dataset
            raster_data, selection = self._data.get_raster_data(plot_inputs)
        except RuntimeError as e:
            error = f"Plot data failed: {str(e)}"
            self._notify(error, "error")
            return plot

        plot_inputs['selection'] = selection

        # Get params needed for plot, such as title, labels, and ticks
        plot_inputs['ms_basename'] = self._ms_info['basename'] # for title
        plot_params = raster_plot_params(raster_data, plot_inputs)
        plot_params['color_limits'] = self._get_color_limits(plot_inputs)

        # Make plot
        try:
            plot = raster_plot(raster_data, plot_params)
        except RuntimeError as e:
            error = f"Plot failed: {str(e)}"
            self._notify(error, "error")
            return plot

        if self._interactive:
            # Update colorbar title with vis axis; plot updates but colorbar does not.
            # plot is hv.Overlay composed of QuadMesh.I (flagged) and QuadMesh.II (unflagged)
            c_label = plot_params['axis_labels']['c']['label']
            if plot_params['colorbar']['flagged']:
                plot.QuadMesh.I = plot.QuadMesh.I.opts(backend_opts={"colorbar.title": "Flagged " + c_label})
            if plot_params['colorbar']['unflagged']:
                plot.QuadMesh.II = plot.QuadMesh.II.opts(backend_opts={"colorbar.title": c_label})
            plot = plot.opts(
                       hv.opts.QuadMesh(tools=['hover'])
                   )

        return plot

    def _do_iter_plot(self, plot_inputs):
        ''' Create one plot per iteration value '''
        iter_axis = plot_inputs['iter_axis']
        iter_values = self._data.get_dimension_values(iter_axis)

        # Init plot before selecting iter values
        self._init_plot(plot_inputs)

        for value in iter_values:
            # Select iteration value and make plot
            self._logger.info("Plot %s iteration value %s", iter_axis, value)
            plot_inputs['selection'][iter_axis] = value
            plot = self._do_plot(plot_inputs)
            self._plots.append(plot)

    def _init_plot(self, plot_inputs):
        ''' Apply selection and set colorbar limits '''
        # Apply user + data_group selection, then select first spw
        # Set data group and name of its correlated data
        self._set_data_group(plot_inputs)

        # Do selection and add spw
        self._data.select_data(plot_inputs['selection'])
        self._select_first_spw()
        self._plot_init = True

        # Print data info
        self._logger.info("Plotting %s msv4 datasets.", self._data.get_num_ms())
        self._logger.info("Maximum dimensions for selected spw: %s", self._data.get_max_data_dims())

    def _select_first_spw(self):
        ''' Determine first spw if not in user selection '''
        if 'spw_name' not in self._plot_inputs['selection']:
            first_spw = self._data.get_first_spw()
            self._plot_inputs['selection']['spw_name'] = first_spw
            self._data.select_data({'spw_name': first_spw})

    def _get_color_limits(self, plot_inputs):
        ''' Calculate stats for color limits for non-interactive amplitude plots. '''
        color_limits = None
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

        # Plot not initialized
        self._plot_init = False

    def _set_data_group(self, plot_inputs):
        ''' Add base data_group to plot inputs selection if not in user selection '''
        if 'selection' not in plot_inputs or not plot_inputs['selection']:
            plot_inputs['selection'] = {}
        if 'data_group' not in plot_inputs['selection']:
            plot_inputs['selection']['data_group'] = 'base'
        if self._data and self._data.is_valid():
            plot_inputs['correlated_data'] = self._data.get_correlated_data(plot_inputs['selection']['data_group'])

    def _notify(self, message, level):
        ''' Log message. '''
        # Placeholder for GUI notifications; use logger for non-gui logging.
        if level == "debug":
            self._logger.debug(message)
        if level == "info":
            self._logger.info(message)
        elif level == "error":
            self._logger.error(message)
        elif level == "success":
            self._logger.info(message)
        elif level == "warning":
            self._logger.warning(message)
