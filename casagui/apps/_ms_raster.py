'''
Implementation of the ``MsRaster`` application for measurement set raster plotting and editing
'''

import time

from casagui.plot._ms_plot import MsPlot
from casagui.data.measurement_set.processing_set._xds_data import VIS_AXIS_OPTIONS
from casagui.data.measurement_set.processing_set._ps_raster_data import AGGREGATOR_OPTIONS
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

        # Validate input arguments
        if not self._data.is_valid():
            raise RuntimeError("Input MS path is invalid or missing, cannot plot")

        # Clear for new plot
        super().clear_selection() # in MsData
        if clear_plots:
            super().clear_plots()

        # Check input values and save ms basename
        plot_inputs = {'x_axis': x_axis, 'y_axis': y_axis, 'vis_axis': vis_axis, 'selection': selection,
            'aggregator': aggregator, 'agg_axis': agg_axis, 'iter_axis': iter_axis, 'title': title}
        self._check_plot_inputs(plot_inputs)
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

        self._logger.info("Plotting %s msv4 datasets.", self._data.get_num_ms())
        self._logger.info("Maximum dimensions for selected spw: %s", self._data.get_max_data_dims())

        # Set colorbar limits for amp vis axis if not interactive (user can adjust interactively)
        self._set_color_limits()

        if self._plot_inputs['iter_axis']:
            self._do_iter_plot()
        else:
            self._do_plot()

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

    def _check_plot_inputs(self, plot_inputs):
        ''' Check plot parameters against Processing Set.  Set data group selection if user did not. '''
        self._check_axis_inputs(plot_inputs)
        self._check_selection_input(plot_inputs)
        self._check_agg_input(plot_inputs)
        if plot_inputs['title'] and not isinstance(plot_inputs['title'], str):
            raise RuntimeError("Invalid parameter type: title must be a string.")
        self._plot_inputs = plot_inputs

    def _check_axis_inputs(self, plot_inputs):
        ''' Check x_axis, y_axis, vis_axis, and iter_axis inputs '''
        # Rename x_axis or y_axis "baseline" for SPECTRUM data dimension
        x_axis = plot_inputs['x_axis']
        y_axis = plot_inputs['y_axis']
        data_dims = self._data.get_data_dimensions()
        x_axis = 'antenna_name' if x_axis == 'baseline' and "antenna_name" in data_dims else x_axis
        y_axis = 'antenna_name' if y_axis == 'baseline' and "antenna_name" in data_dims else y_axis
        if x_axis not in data_dims or y_axis not in data_dims:
            raise ValueError(f"Invalid parameter value: select x and y axis from {data_dims}.")
        plot_inputs['data_dims'] = data_dims
        plot_inputs['x_axis'] = x_axis
        plot_inputs['y_axis'] = y_axis

        if plot_inputs['vis_axis'] not in VIS_AXIS_OPTIONS:
            raise ValueError(f"Invalid parameter value: vis_axis {plot_inputs['vis_axis']}. Options include {VIS_AXIS_OPTIONS}")

        iter_axis = plot_inputs['iter_axis']
        if iter_axis and (iter_axis not in data_dims or iter_axis in (x_axis, y_axis)):
            raise RuntimeError(f"Invalid parameter value: iteration axis {iter_axis}. Must be dimension which is not a plot axis.")

    def _check_selection_input(self, plot_inputs):
        ''' Check selection type and data_group selection.  Make copy of user selection. '''
        selection = plot_inputs['selection']
        if selection:
            # Use a copy so that automatic selections do not change user's selection
            if not isinstance(selection, dict):
                raise RuntimeError("Invalid parameter type: selection must be dictionary.")
            if 'data_group' in selection and selection['data_group'] not in self._data.get_data_groups():
                raise ValueError(f"Invalid parameter value: data_group {selection['data_group']}. Use data_groups() to see options.")
            plot_inputs['selection'] = selection.copy()

    def _check_agg_input(self, plot_inputs):
        ''' Check aggregator and agg_axis. Set agg_axis if not set. '''
        aggregator = plot_inputs['aggregator']
        agg_axis = plot_inputs['agg_axis']

        if aggregator and aggregator not in AGGREGATOR_OPTIONS:
            raise RuntimeError(f"Invalid parameter value: aggregator {aggregator}. Options include {AGGREGATOR_OPTIONS}.")

        if agg_axis:
            if not isinstance(agg_axis, str) and not isinstance(agg_axis, list):
                raise RuntimeError(f"Invalid parameter value: agg axis {agg_axis}. Options include one or more dimensions {plot_inputs['data_dims']}.")
            if isinstance(agg_axis, str):
                agg_axis = [agg_axis]
            for axis in agg_axis:
                if axis not in plot_inputs['data_dims'] or axis in (plot_inputs['x_axis'], plot_inputs['y_axis']):
                    raise RuntimeError(f"Invalid parameter value: aggregator axis {axis}. Must be dimension which is not a plot axis.")
        elif aggregator:
            # Set agg_axis to non-plotted dim axes
            agg_axis = plot_inputs['data_dims'].copy()
            agg_axis.remove(plot_inputs['x_axis'])
            agg_axis.remove(plot_inputs['y_axis'])
        plot_inputs['agg_axis'] = agg_axis

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
            self._logger.info("Setting colorbar limits: (%.4f, %.4f).", color_limits[0], color_limits[1])
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
        self._logger.debug("Stats elapsed time: %.2fs.", time.time() - start)
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

            self._plots.append(plot)


    def _do_iter_plot(self):
        ''' Create one plot per iteration value '''
        iter_axis = self._plot_inputs['iter_axis']
        iter_values = self._data.get_dimension_values(iter_axis)
        if iter_values:
            for value in iter_values:
                # Select iteration value and make plot
                self._logger.info("Plot %s iteration value %s", iter_axis, value)
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
