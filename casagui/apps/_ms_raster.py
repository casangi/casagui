'''
Implementation of the ``MsRaster`` application for measurement set raster plotting and editing
'''

import time

from bokeh.models.formatters import NumeralTickFormatter
import holoviews as hv
import numpy as np
import panel as pn
from pandas import to_datetime

from casagui.bokeh.format import get_time_formatter
from casagui.bokeh.state._palette import available_palettes
from casagui.plot.ms_plot._ms_plot import MsPlot
from casagui.plot.ms_plot._ms_plot_constants import VIS_AXIS_OPTIONS, SPECTRUM_AXIS_OPTIONS
from casagui.plot.ms_plot._ms_plot_selectors import (file_selector, title_selector, style_selector, axis_selector,
aggregation_selector, iteration_selector, selection_selector, plot_starter)
from casagui.plot.ms_plot._raster_plot_inputs import check_inputs
from casagui.plot.ms_plot._raster_plot import RasterPlot

class MsRaster(MsPlot):
    '''
    Plot MeasurementSet data as raster plot.

    Args:
        ms (str): path to MSv2 (.ms) or MSv4 (.zarr) file. Required when show_gui=False.
        log_level (str): logging threshold. Options include 'debug', 'info', 'warning', 'error', 'critical'. Default 'info'.
        show_gui (bool): whether to launch the interactive GUI in a browser tab. Default False.

    Example:
        from casagui.plots import MsRaster
        msr = MsRaster(ms='myvis.ms')
        msr.summary()
        msr.set_style_params(unflagged_cmap='Plasma', flagged_cmap='Greys', show_colorbar=True)
        msr.plot(x_axis='frequency', y_axis='time', vis_axis='amp', data_group='base')
        msr.show()
        msr.save() # saves as {ms name}_raster.png
    '''

    def __init__(self, ms=None, log_level="info", show_gui=False):
        super().__init__(ms, log_level, show_gui, "MsRaster")
        self._raster_plot = RasterPlot()

        # Calculations for color limits
        self._spw_stats = {}
        self._spw_color_limits = {}

        if show_gui:
            # GUI based on panel widgets
            self._gui_layout = None

            # Check if plot inputs changed and new plot is needed.
            # GUI can change subparams which do not change plot
            self._last_plot_inputs = None
            self._last_style_inputs = None
            # Last plot when no new plot created (plot inputs same) or is iter Layout plot (opened in tab)
            self._last_gui_plot = None

            # Return plot for gui DynamicMap:
            # Empty plot when ms not set or plot fails
            self._empty_plot = self._create_empty_plot()

            # Set default style and plot inputs to use when launching gui
            self.set_style_params()
            self.plot()
            self._launch_gui()

            # Set filename TextInput to input ms to trigger plot
            if 'ms' in self._ms_info and self._ms_info['ms']:
                self._set_filename([self._ms_info['ms']]) # function expects list

    def colormaps(self):
        ''' List available colormap (Bokeh palettes). '''
        return available_palettes()

    def set_style_params(self, unflagged_cmap='Viridis', flagged_cmap='Reds', show_colorbar=True, show_flagged_colorbar=True):
        '''
            Set styling parameters for the plot, such as colormaps and whether to show colorbar.
            Placeholder for future styling such as fonts.

            Args:
                unflagged_cmap (str): colormap to use for unflagged data.
                flagged_cmap (str): colormap to use for flagged data.
                show_colorbar (bool): Whether to show colorbar with plot.  Default True.
        '''
        cmaps = self.colormaps()
        if unflagged_cmap not in cmaps:
            raise ValueError(f"{unflagged_cmap} not in colormaps list: {cmaps}")
        if flagged_cmap not in cmaps:
            raise ValueError(f"{flagged_cmap} not in colormaps list: {cmaps}")
        self._raster_plot.set_style_params(unflagged_cmap, flagged_cmap, show_colorbar, show_flagged_colorbar)

# pylint: disable=too-many-arguments, too-many-positional-arguments, too-many-locals, unused-argument
    def plot(self, x_axis='baseline', y_axis='time', vis_axis='amp', selection=None, aggregator=None, agg_axis=None,
             iter_axis=None, iter_range=None, subplots=None, color_mode=None, color_range=None, title=None, clear_plots=True):
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
                ProcessingSet selection: by summary column names. Call summary() to see options.
                    'query': for pandas query of summary() columns.
                    Default: select first spw (by id).
                MeasurementSet selection:
                    'data_group': name for correlated data, flags, weights, and uvw. Default value 'base'.
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
            iter_axis (str): dimension over which to iterate values (using iter_range).
            iter_range (tuple): (start, end) inclusive index values for iteration plots.
                Default (0, 0) (first iteration only). Use (0, -1) for all iterations.
                If subplots is a grid, the range is limited by the grid size.
                If subplots is a single plot, all iteration plots in the range can be saved using export_range in save().
            subplots (None, tuple): set a grid of (rows, columns).  None = (1, 1) for single plot.
                Use with iter_axis and iter_range, or clear_plots=False.
                If used in multiple calls, the last subplots tuple will be used to determine grid to show or save.
            color_mode (None, str): Whether to limit range of colorbar.  Default None (no limit).
                Options include None (use data limits), 'auto' (calculate limits for amplitude), and 'manual' (use range in color_range).
                'auto' is equivalent to None if vis_axis is not 'amp'.
                When subplots is set, the 'auto' or 'manual' range will be used for all plots.
            color_range (tuple): (min, max) of colorbar to use if color_mode is 'manual'.
            title (str): Plot title, default None (no title)
                Set title='ms' to generate title from ms name and iter_axis value, if any.
            clear_plots (bool): whether to clear list of plots. Default True.

        If not show_gui and plotting is successful, use show() or save() to view/save the plot only.
        '''
        inputs = locals() # collect arguments into dict (not unused as pylint complains!)

        start = time.time()

        # Clear for new plot
        self._reset_plot(clear_plots)

        # Get data dimensions if valid MS is set to check input axes
        if 'data_dims' in self._ms_info:
            data_dims = self._ms_info['data_dims']
            if 'baseline_id' in data_dims:
                data_dims.remove('baseline_id')
                data_dims.append('baseline')
            inputs['data_dims'] = data_dims

        # Validate input arguments; data dims needed to check input and rename baseline dimension
        check_inputs(inputs)
        self._plot_inputs = inputs

        # Copy user selection dict; selection will be modified for plot
        if inputs['selection']:
            self._plot_inputs['selection'] = inputs['selection'].copy()

        if not self._show_gui:
            # Cannot plot if no MS
            if not self._data or not self._data.is_valid():
                raise RuntimeError("Cannot plot MS: input MS path is invalid or missing.")

            # Create raster plot and add to plot list
            try:
                if self._plot_inputs['iter_axis']:
                    self._do_iter_plot(self._plot_inputs)
                else:
                    plot = self._do_plot(self._plot_inputs)
                    self._plots.append(plot)
            except RuntimeError as e:
                error = f"Plot failed: {str(e)}"
                super()._notify(error, "error", 0)

            self._logger.debug("Plot elapsed time: %.2fs.", time.time() - start)
# pylint: enable=too-many-arguments, too-many-positional-arguments, too-many-locals, unused-argument

    def save(self, filename='', fmt='auto', width=900, height=600):
        '''
        Save plot to file.

        Args:
            filename (str): Name of file to save. Default '': the plot will be saved as {ms}_raster.{ext}.
                If fmt is not set for extension, plot will be saved as .png.
            fmt (str): Format of file to save ('png', 'svg', 'html', or 'gif').
                Default 'auto': inferred from filename extension.
            width (int): width of exported plot.
            height (int): height of exported plot.

        If iteration plots were created:
            If subplots is a grid, the layout plot will be saved to a single file.
            If subplots is a single plot, iteration plots will be saved individually,
                with a plot index appended to the filename: {filename}_{index}.{ext}.
        '''
        if not filename:
            filename = f"{self._ms_info['basename']}_raster.png"
        super().save(filename, fmt, width, height)

    def _do_plot(self, plot_inputs):
        ''' Create plot using plot inputs '''
        if not self._plot_init:
            self._init_plot(plot_inputs)

        # Select vis_axis data to plot and update selection; returns xarray Dataset
        raster_data = self._data.get_raster_data(plot_inputs)

        # Add params needed for plot: auto color range and ms name
        self._set_auto_color_range(plot_inputs) # set calculated limits if auto mode
        ms_name = self._ms_info['basename'] # for title
        self._raster_plot.set_plot_params(raster_data, plot_inputs, ms_name)

        # Make plot. Add data min/max if GUI is shown to update color limits range.
        return self._raster_plot.raster_plot(raster_data, self._logger, self._show_gui)

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

        # Plot the minimum of iter range or subplots number of plots
        num_subplots = np.prod(subplots) if subplots else 1
        num_iter_plots = min(num_iter_plots, num_subplots) if num_subplots > 1 else num_iter_plots
        end_idx = start_idx + num_iter_plots

        # Init plot before selecting iter values
        self._init_plot(plot_inputs)

        for i in range(start_idx, end_idx):
            # Select iteration value and make plot
            value = iter_values[i]
            self._logger.info("Plot %s iteration index %s value %s", iter_axis, i, value)
            plot_inputs['selection'][iter_axis] = value
            plot = self._do_plot(plot_inputs)
            self._plots.append(plot)

    def _init_plot(self, plot_inputs):
        ''' Apply automatic selection '''
        # Apply user + data_group selection, then select first spw
        # Set data group and name of its correlated data
        self._set_data_group(plot_inputs)

        # Do selection and add spw
        self._data.select_data(plot_inputs['selection'])
        self._select_first_spw(plot_inputs)

        # Clear automatic or iter selection of unplotted dimensions
        if 'dim_selection' in self._plot_inputs:
            del self._plot_inputs['dim_selection']

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

    def _set_auto_color_range(self, plot_inputs):
        ''' Calculate stats for color limits for non-gui amplitude plots. '''
        color_mode = plot_inputs['color_mode']
        color_limits = None

        if color_mode == 'auto':
            if plot_inputs['vis_axis']=='amp' and not plot_inputs['aggregator']:
                # For amplitude, limit colorbar range using stored per-spw ms stats
                spw_name = plot_inputs['selection']['spw_name']
                if spw_name in self._spw_color_limits:
                    color_limits = self._spw_color_limits[spw_name]
                else:
                    # Select spw name and data group only
                    spw_data_selection = {'spw_name': spw_name, 'data_group_name': plot_inputs['selection']['data_group_name']}
                    color_limits = self._calc_amp_color_limits(spw_data_selection)
                    self._spw_color_limits[spw_name] = color_limits
        plot_inputs['auto_color_range'] = color_limits

        if color_limits:
            self._logger.info("Setting amplitude color range: (%.4f, %.4f).", color_limits[0], color_limits[1])
        elif color_mode is None:
            self._logger.info("Autoscale color range")
        else:
            self._logger.info("Using manual color range: %s", plot_inputs['color_range'])

    def _calc_amp_color_limits(self, selection):
        # Calculate colorbar limits from amplitude stats for unflagged data in selected spw
        self._logger.info("Calculating stats for colorbar limits.")
        start = time.time()

        ms_stats = self._data.get_vis_stats(selection, 'amp')
        self._spw_stats['spw_name'] = ms_stats
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

        # Reset selection in data and dim selection in plot inputs
        super().clear_selection()

        # Reset params set for last plot
        self._raster_plot.reset_plot_params()

        self._plot_init = False

    def _set_data_group(self, plot_inputs):
        ''' Add base data_group to plot inputs selection if not in user selection '''
        if 'selection' not in plot_inputs or not plot_inputs['selection']:
            plot_inputs['selection'] = {}

        data_group = 'base'
        if 'data_group' in plot_inputs['selection']:
            data_group = plot_inputs['selection'].pop('data_group')
        plot_inputs['selection']['data_group_name'] = data_group

        if self._data and self._data.is_valid():
            plot_inputs['correlated_data'] = self._data.get_correlated_data(data_group)

    ### -----------------------------------------------------------------------
    ### Interactive GUI
    ### -----------------------------------------------------------------------
    def _launch_gui(self):
        ''' Use Holoviz Panel to create a dashboard for plot inputs. '''
        # Select MS
        file_selectors = file_selector('Path to MeasurementSet (ms or zarr) for plot', '~' , self._set_filename)

        # Select style - colormaps, colorbar, color limits
        style_selectors = style_selector(self._set_style_params, self._set_color_range)

        # Set title
        title_input = title_selector(self._set_title)

        # Select x, y, and vis axis
        x_axis = self._plot_inputs['x_axis']
        y_axis = self._plot_inputs['y_axis']
        data_dims = self._ms_info['data_dims'] if 'data_dims' in self._ms_info else None
        axis_selectors = axis_selector(x_axis, y_axis, data_dims, True, self._set_axes)

        # Select from ProcessingSet and MeasurementSet
        selection_selectors = selection_selector(self._set_ps_selection)

        # Generic axis options, updated when ms is set
        axis_options = data_dims if data_dims else []

        # Select aggregator and axes to aggregate
        agg_selectors = aggregation_selector(axis_options, self._set_aggregation)

        # Select iter_axis and iter value or range
        iter_selectors = iteration_selector(axis_options, self._set_iter_values, self._set_iteration)

        # Put user input widgets in accordion with only one card active at a time
        selectors = pn.Accordion(
            ("Select file", file_selectors),    # [0]
            ("Plot style", style_selectors),    # [1]
            ("Plot axes", axis_selectors),      # [2]
            ("Selection", selection_selectors), # [3]
            ("Aggregation", agg_selectors),     # [4]
            ("Iteration", iter_selectors),      # [5]
            ("Plot title", title_input),        # [6]
        )
        selectors.toggle = True

        # Plot button and spinner while plotting
        init_plot = plot_starter(self._update_plot_spinner)

        # Connect plot to filename and selector widgets
        dmap = hv.DynamicMap(
            pn.bind(
                self._update_plot,
                ms=file_selectors[0][0],
                do_plot=init_plot[0],
            ),
        )

        # Layout plot and input widgets in a row
        self._gui_layout = pn.Row(
            pn.Column(           # [0]
                dmap,
                sizing_mode='stretch_width',
            ),
            pn.Spacer(width=10), # [1]
            pn.Column(           # [2]
                pn.Spacer(height=25), # [0]
                selectors,            # [1]
                init_plot,            # [2]
                width_policy='min',
                width=400,
                sizing_mode='stretch_height',
            ),
            sizing_mode='stretch_height',
        )

        # Show gui
        # print("gui layout:", self._gui_layout) # for debugging
        self._gui_layout.show(title=self._app_name, threaded=True)

    ###
    ### Main callback to create plot
    ###
    def _update_plot(self, ms, do_plot):
        ''' Create plot with inputs from GUI.  Must return plot, even if empty plot, for DynamicMap. '''
        if self._toast:
            self._toast.destroy()

        self._get_selector("selectors").active = []
        if not ms:
            # Launched GUI with no MS
            return self._empty_plot

        # If not first plot, user has to click Plot button (do_plot=True).
        first_plot = not self._last_gui_plot
        if not do_plot and not first_plot:
            # Not ready to update plot yet, return last plot.
            return self._last_gui_plot

        if (self._set_ms(ms) or first_plot) and self._data and self._data.is_valid():
            # New MS set and is valid
            self._plot_inputs['selection'] = None
            self._update_gui_axis_options()

        # Add ms path to detect change and make new plot
        self._plot_inputs['ms'] = ms

        # Do new plot or resend last plot
        self._reset_plot()
        gui_plot = None

        style_inputs = self._raster_plot.get_plot_params()['style']
        if self._inputs_changed(style_inputs):
            # First plot or changed plot
            try:
                # Check inputs from GUI then plot
                self._plot_inputs['data_dims'] = self._ms_info['data_dims']
                check_inputs(self._plot_inputs)
                gui_plot = self._do_gui_plot()
            except (ValueError, TypeError) as e:
                # Clear plot, inputs invalid
                self._notify(str(e), 'error', 0)
                gui_plot = self._empty_plot
            except RuntimeError as e:
                # Clear plot, plot failed
                self._notify(str(e), 'error', 0)
                gui_plot = self._empty_plot
        else:
            # Subparam values changed but not applied to plot
            gui_plot = self._last_gui_plot

        # Save inputs to see if changed
        self._last_plot_inputs = self._plot_inputs.copy()
        self._last_style_inputs = style_inputs.copy()
        self._last_plot_inputs['selection'] = self._plot_inputs['selection'].copy()
        if first_plot and not do_plot:
            self._plot_inputs['selection'].clear()

        # Save plot if no new plot
        self._last_gui_plot = gui_plot

        # Change plot button and stop spinner
        self._update_plot_status(False)
        self._update_plot_spinner(False)

        return gui_plot

    def _inputs_changed(self, style_inputs):
        ''' Check if inputs changed and need new plot '''
        if not self._last_plot_inputs:
            return True

        # Cannot use plot_inputs == self._plot_inputs until selection in GUI.
        # Check inputs one by one
        for key in self._plot_inputs:
            if not self._values_equal(self._plot_inputs[key], self._last_plot_inputs[key]):
                return True

        for key in style_inputs:
            if not self._values_equal(style_inputs[key], self._last_style_inputs[key]):
                return True
        return False

    def _values_equal(self, val1, val2):
        if val1 and val2: # both set
            return val1 == val2

        if not val1 and not val2: # both None
            return True

        return False # one set and other is None

    ###
    ### Create plot for DynamicMap
    ###
    def _do_gui_plot(self):
        ''' Create plot based on gui plot inputs '''
        if self._data and self._data.is_valid():
            try:
                if self._plot_inputs['iter_axis']:
                    # Make iter plot (possibly with subplots layout)
                    self._do_iter_plot(self._plot_inputs)
                    subplots = self._plot_inputs['subplots']
                    layout_plot, is_layout = super()._layout_plots(subplots)

                    if is_layout:
                        # Cannot show Layout in DynamicMap, show in new tab
                        super().show()
                        self._logger.info("Plot update complete")
                        return self._last_gui_plot
                    # Overlay raster plot for DynamicMap
                    self._logger.info("Plot update complete")
                    return layout_plot

                # Make single Overlay raster plot for DynamicMap
                plot = self._do_plot(self._plot_inputs)
                plot_params = self._raster_plot.get_plot_params()

                # Update color limits in gui with data range
                self._update_color_range(plot_params)

                # Update colorbar labels and limits
                plot.QuadMesh.I = self._set_plot_colorbar(plot.QuadMesh.I, plot_params, "flagged")
                plot.QuadMesh.II = self._set_plot_colorbar(plot.QuadMesh.II, plot_params, "unflagged")

                self._logger.info("Plot update complete")
                return plot.opts(
                    hv.opts.QuadMesh(tools=['hover'])
                )
            except RuntimeError as e:
                error = f"Plot failed: {str(e)}"
                super()._notify(error, "error", 0)

        # Make single Overlay raster plot for DynamicMap
        return self._empty_plot

    def _create_empty_plot(self):
        ''' Create empty Overlay plot for DynamicMap with default color params and hover enabled '''
        plot_params = self._raster_plot.get_plot_params()
        plot = hv.Overlay(
            hv.QuadMesh([]).opts(
                colorbar=False,
                cmap=plot_params['style']['flagged_cmap'],
                responsive=True,
            ) * hv.QuadMesh([]).opts(
                colorbar=plot_params['style']['show_colorbar'],
                cmap=plot_params['style']['unflagged_cmap'],
                responsive=True,
            )
        )
        return plot.opts(
            hv.opts.QuadMesh(tools=['hover'])
        )

    def _set_plot_colorbar(self, plot, plot_params, plot_type):
        ''' Update plot colorbar labels and limits
                plot_type is "unflagged" or "flagged"
        '''
        # Update colorbar labels if shown, else hide
        colorbar_key = plot_type + '_colorbar'
        if plot_params['plot'][colorbar_key]:
            c_label = plot_params['plot']['axis_labels']['c']['label']
            cbar_title = "Flagged " + c_label if plot_type == "flagged" else c_label

            plot = plot.opts(
                colorbar=True,
                backend_opts={
                    "colorbar.title": cbar_title,
                }
            )
        else:
            plot = plot.opts(
                colorbar=False,
            )

        # Update plot color limits
        color_limits = plot_params['plot']['color_limits']
        if color_limits:
            plot = plot.opts(
                clim=color_limits,
            )

        return plot

    def _update_color_range(self, plot_params):
        ''' Set the start/end range on the colorbar to min/max of plot data '''
        if self._gui_layout and 'data' in plot_params and 'data_range' in plot_params['data']:
            # Update range slider start and end to data min and max
            data_range = plot_params['data']['data_range']
            style_selectors = self._get_selector('style')
            range_slider = style_selectors[3][1]
            range_slider.start = data_range[0]
            range_slider.end = data_range[1]

    ###
    ### Update widget options based on MS
    ###
    def _get_selector(self, name):
        ''' Return selector group for name, for setting options '''
        selectors = self._gui_layout[2][1]
        selectors_index = {'file': 0, 'style': 1, 'axes': 2, 'selection': 3, 'agg': 4, 'iter': 5, 'title': 6}
        if name == "selectors":
            return selectors
        return selectors[selectors_index[name]]

    def _update_gui_axis_options(self):
        ''' Set gui options from ms data '''
        if 'data_dims' in self._ms_info:
            data_dims = self._ms_info['data_dims']

            # Update options for x_axis and y_axis selectors
            axis_selectors = self._get_selector('axes')
            axis_selectors.objects[0][0].options = data_dims
            axis_selectors.objects[0][1].options = data_dims

            # Update options for vis_axis selector
            if self._data.get_correlated_data('base') == 'SPECTRUM':
                axis_selectors.objects[1].options = SPECTRUM_AXIS_OPTIONS
            else:
                axis_selectors.objects[1].options = VIS_AXIS_OPTIONS

            # Update options for agg axes selector
            agg_selectors = self._get_selector('agg')
            agg_selectors[1].options = data_dims

            # Update options for iteration axis selector
            iter_selectors = self._get_selector('iter')
            iter_axis_selector = iter_selectors[0][0]
            iter_axis_selector.options = ['None']
            iter_axis_selector.options.extend(data_dims)

    ###
    ### Callbacks for widgets which update other widgets
    ###
    def _set_filename(self, filename):
        ''' Set filename in text box from file selector value (list) '''
        if filename and self._gui_layout:
            file_selectors = self._get_selector('file')

            # Collapse FileSelector card
            file_selectors[1].collapsed = True

            # Change plot button color to indicate change unless ms path not set previously
            filename_input = file_selectors[0][0]
            if filename_input.value:
                self._update_plot_status(True)

            # Set filename from last file in file selector (triggers _update_plot())
            #filename_input.width = len(filename[-1])
            filename_input.value = filename[-1]


    def _set_iter_values(self, iter_axis):
        ''' Set up player with values when iter_axis is selected '''
        iter_axis = None if iter_axis == 'None' else iter_axis
        if iter_axis and self._gui_layout:
            iter_values = self._data.get_dimension_values(iter_axis)
            if iter_values:

                iter_selectors = self._get_selector('iter')

                # Update value selector with values and select first value
                iter_value_player = iter_selectors[1][0]
                if iter_axis == 'time':
                    if isinstance(iter_values[0], float):
                        iter_values = self._get_datetime_values(iter_values)
                    iter_value_player.format = get_time_formatter()
                elif iter_axis == 'frequency':
                    iter_value_player.format = NumeralTickFormatter(format='0,0.0000000')

                iter_value_player.options = iter_values
                iter_value_player.value = iter_values[0]
                iter_value_player.show_value = True

                # Update range inputs end values and select first
                iter_range_inputs = iter_selectors[1][1]
                last_iter_index = len(iter_values) - 1
                # range start
                iter_range_inputs[0][0].end = last_iter_index
                iter_range_inputs[0][0].value = 0
                # range end
                iter_range_inputs[0][1].end = last_iter_index
                iter_range_inputs[0][1].value = 0

    def _get_datetime_values(self, float_times):
        ''' Return list of float time values as list of datetime values for gui options '''
        time_attrs = self._data.get_dimension_attrs('time')
        datetime_values = []
        try:
            datetime_values = to_datetime(float_times, unit=time_attrs['units'], origin=time_attrs['format'])
        except TypeError:
            datetime_values = to_datetime(float_times, unit=time_attrs['units'][0], origin=time_attrs['format'])
        return list(datetime_values)

    def _update_plot_spinner(self, plot_clicked):
        ''' Callback to start spinner when Plot button clicked. '''
        if self._gui_layout:
            # Start spinner
            spinner = self._gui_layout[2][2][1]
            spinner.value = plot_clicked

    def _update_plot_status(self, inputs_changed):
        ''' Change button color when inputs change. '''
        if self._gui_layout:
            # Set button color
            button = self._gui_layout[2][2][0]
            button.button_style = 'solid' if inputs_changed else 'outline'

    ###
    ### Callbacks for widgets which update plot inputs
    ###
    def _set_title(self, title):
        ''' Set title from gui text input '''
        self._plot_inputs['title'] = title
        self._update_plot_status(True) # Change plot button to solid

    def _set_style_params(self, unflagged_cmap, flagged_cmap, show_colorbar, show_flagged_colorbar):
        self.set_style_params(unflagged_cmap, flagged_cmap, show_colorbar, show_flagged_colorbar)
        self._update_plot_status(True) # Change plot button to solid

    def _set_color_range(self, color_mode, color_range):
        ''' Set style params from gui '''
        color_mode = color_mode.split()[0]
        color_mode = None if color_mode == 'No' else color_mode
        self._plot_inputs['color_mode'] = color_mode
        self._plot_inputs['color_range'] = color_range
        self._update_plot_status(True) # Change plot button to solid

    def _set_axes(self, x_axis, y_axis, vis_axis):
        ''' Set plot axis params from gui '''
        self._plot_inputs['x_axis'] = x_axis
        self._plot_inputs['y_axis'] = y_axis
        self._plot_inputs['vis_axis'] = vis_axis
        self._update_plot_status(True) # Change plot button to solid

    def _set_aggregation(self, aggregator, agg_axes):
        ''' Set aggregation params from gui '''
        aggregator = None if aggregator== 'None' else aggregator
        self._plot_inputs['aggregator'] = aggregator
        self._plot_inputs['agg_axis'] = agg_axes # ignored if aggregator not set
        self._update_plot_status(True) # Change plot button to solid

# pylint: disable=too-many-arguments, too-many-positional-arguments
    def _set_iteration(self, iter_axis, iter_value_type, iter_value, iter_start, iter_end, subplot_rows, subplot_columns):
        ''' Set iteration params from gui '''
        iter_axis = None if iter_axis == 'None' else iter_axis
        self._plot_inputs['iter_axis'] = iter_axis
        self._plot_inputs['subplots'] = (subplot_rows, subplot_columns)

        if iter_axis:
            if iter_value_type == 'By Value':
                # Use index of iter_value for tuple
                if self._data and self._data.is_valid():
                    iter_values = self._data.get_dimension_values(iter_axis)
                    iter_index = iter_values.index(iter_value)
                    self._plot_inputs['iter_range'] = (iter_index, iter_index)
            else:
                # 'By Range': use range start and end values for tuple
                self._plot_inputs['iter_range'] = (iter_start, iter_end)
        else:
            self._plot_inputs['iter_range'] = None
        self._update_plot_status(True) # Change plot button to solid
# pylint: enable=too-many-arguments, too-many-positional-arguments

    def _set_ps_selection(self, query):
        ''' Select ProcessingSet from gui using summary columns '''
        if 'selection' not in self._plot_inputs or self._plot_inputs['selection'] is None:
            self._plot_inputs['selection'] = {}
        self._plot_inputs['selection']['query'] = query
        self._update_plot_status(True) # Change plot button to solid
