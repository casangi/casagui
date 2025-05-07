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
from casagui.plot._ms_plot import MsPlot
from casagui.plot._ms_plot_constants import VIS_AXIS_OPTIONS, SPECTRUM_AXIS_OPTIONS, PLOT_WIDTH, PLOT_HEIGHT
from casagui.plot._panel_selectors import file_selector, title_selector, style_selector, axis_selector, aggregation_selector, iteration_selector, selection_selector, plot_starter
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
        msr.set_style_params(unflagged_cmap='Plasma', flagged_cmap='Greys', colorbar=True)
        msr.plot(x_axis='frequency', y_axis='time', vis_axis='amp', data_group='base')
        msr.show()
        msr.save() # saves as {ms name}_raster.png
    '''

    def __init__(self, ms=None, log_level="info", interactive=False):
        super().__init__(ms, log_level, interactive, "MsRaster")
        self._raster_plot = RasterPlot()

        # Calculations for color limits
        self._spw_stats = {}
        self._spw_color_limits = {}

        if interactive:
            # GUI based on panel widgets
            self._gui_layout = None

            # Empty plot for gui DynamicMap when ms not set or plot fails
            self._empty_plot = self._create_empty_plot()

            # Return last plot for gui DynamicMap when no new plot created or iter Layout plot
            self._last_gui_plot = None

            # Set default style and plot inputs to use when launching gui
            self.set_style_params()
            self.plot()
            self._launch_gui()

            # Set filename TextInput to input ms to trigger plot
            if 'ms' in self._ms_info and self._ms_info['ms']:
                self._set_filename([self._ms_info['ms']]) # function expects list

    def set_ms(self, ms):
        ''' Set MS path for current MsRaster '''
        ms_changed = super()._set_ms(ms)
        if ms_changed:
            self._raster_plot.reset_data_params()
            self._spw_color_limits = {}
        return ms_changed

    def get_colormaps(self):
        ''' List available colormap (Bokeh palettes). '''
        return available_palettes()

    def set_style_params(self, unflagged_cmap='Viridis', flagged_cmap='Reds', show_colorbar=True):
        '''
            Set styling parameters for the plot, such as colormaps and whether to show colorbar.
            Placeholder for future styling such as fonts.

            Args:
                unflagged_cmap (str): colormap to use for unflagged data.
                flagged_cmap (str): colormap to use for flagged data.
                show_colorbar (bool): Whether to show colorbar with plot.  Default True.
        '''
        cmaps = self.get_colormaps()
        if unflagged_cmap not in cmaps:
            raise ValueError(f"{unflagged_cmap} not in colormaps list: {cmaps}")
        if flagged_cmap not in cmaps:
            raise ValueError(f"{flagged_cmap} not in colormaps list: {cmaps}")
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
            title (str): Plot title, default None (generate title from ms name and iter_axis value if any).
            clear_plots (bool): whether to clear list of plots. Default True.

        If not interactive and plotting is successful, use show() or save() to view/save the plot only.
        '''
        inputs = locals() # collect arguments into dict (not unused as pylint complains!)

        start = time.time()

        # Clear for new plot
        self._reset_plot(clear_plots)

        # Get data dimensions if valid MS is set to check input axes
        if self._data and self._data.is_valid():
            inputs['data_dims'] = self._ms_info['data_dims']

        # Validate input arguments; data dims needed to check input and rename baseline dimension
        check_inputs(inputs)
        self._plot_inputs = inputs

        # Copy user selection dict; selection will be modified for plot
        if inputs['selection']:
            self._plot_inputs['selection'] = inputs['selection'].copy()

        if not self._interactive:
            # Cannot plot if no MS
            if not self._data or not self._data.is_valid():
                raise RuntimeError("Cannot plot MS: input MS path is invalid or missing.")

            # Create raster plot and add to plot list
            try:
                if self._plot_inputs['iter_axis']:
                    self._do_iter_plot(self._plot_inputs)
                else:
                    plot, _ = self._do_plot(self._plot_inputs)
                    self._plots.append(plot)
            except RuntimeError as e:
                error = f"Plot failed: {str(e)}"
                super()._notify(error, "error", 0)

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

    def _get_colormaps(self, provider=None, category=None):
        return hv.plotting.list_cmaps(provider=provider, category=category, reverse=False)

    def _do_plot(self, plot_inputs):
        ''' Create plot using plot inputs '''
        if not self._plot_init:
            self._init_plot(plot_inputs)

        # Select vis_axis data to plot and update selection; returns xarray Dataset
        raster_data = self._data.get_raster_data(plot_inputs)

        # Set params needed for plot
        plot_inputs['color_limits'] = self._get_color_limits(plot_inputs) # update with calculated limits if not user-set
        ms_name = self._ms_info['basename'] # for title
        self._raster_plot.set_data_params(raster_data, plot_inputs, ms_name)

        # Make plot. Return plot info if interactive GUI.
        return self._raster_plot.raster_plot(raster_data, self._logger, self._interactive)

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

        # Automatic or iter selection of unplotted dimensions
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

    ### -----------------------------------------------------------------------
    ### Interactive GUI
    ### -----------------------------------------------------------------------
    def _launch_gui(self):
        ''' Use Holoviz Panel to create a dashboard for plot inputs. '''
        # Select MS
        file_selectors = file_selector('MeasurementSet (ms or zarr) to plot', '~' , self._set_filename)

        # Set title
        title_input = title_selector()

        # Select style - colormaps, colorbar, color limits
        style_selectors = style_selector()

        # Select x, y, and vis axis
        x_axis = self._plot_inputs['x_axis']
        y_axis = self._plot_inputs['y_axis']
        data_dims = self._ms_info['data_dims'] if 'data_dims' in self._ms_info else None
        axis_selectors = axis_selector(x_axis, y_axis, data_dims)

        # Generic axis options, updated when ms is set
        axis_options = data_dims if data_dims else []

        # Select aggregator and axes to aggregate
        agg_selectors = aggregation_selector(axis_options)

        # Select iter_axis and iter_value
        iter_selectors = iteration_selector(axis_options, self._set_iter_values)

        # Select from ProcessingSet and MeasurementSet
        selection_selectors = selection_selector()

        # Put user input widgets in accordion with only one card active at a time
        selectors = pn.Accordion(
            ("Select file", file_selectors),    # [0]
            ("Plot title", title_input),        # [1]
            ("Plot style", style_selectors),    # [2]
            ("Plot axes", axis_selectors),      # [3]
            ("Aggregation", agg_selectors),     # [4]
            ("Iteration", iter_selectors),      # [5]
            ("Selection", selection_selectors), # [6]
        )
        selectors.toggle = True

        # Plot button and spinner while plotting
        init_plot = plot_starter(self._update_plot_spinner)

        # Connect plot to filename and selector widgets
        dmap = hv.DynamicMap(pn.bind(
            self._update_plot,
            ms=file_selectors[0][0],
            title=title_input,
            unflagged_cmap=style_selectors[0][0],
            flagged_cmap=style_selectors[0][1],
            show_colorbar=style_selectors[0][2],
            auto_color_limits=style_selectors[1][0],
            color_limits=style_selectors[1][1],
            x_axis=axis_selectors[0][0],
            y_axis=axis_selectors[0][1],
            vis_axis=axis_selectors[1],
            aggregator=agg_selectors[0],
            agg_axis=agg_selectors[1],
            iter_axis=iter_selectors[0][0],
            iter_value_type=iter_selectors[0][1],
            iter_value=iter_selectors[1][0],
            iter_range_start=iter_selectors[1][1][0][0],
            iter_range_end=iter_selectors[1][1][0][1],
            subplot_rows=iter_selectors[1][1][1][0],
            subplot_columns=iter_selectors[1][1][1][1],
            do_plot=init_plot[0],
        )).opts(
            width=PLOT_WIDTH, height=PLOT_HEIGHT
        )


        # Layout plot and input widgets in a row
        self._gui_layout = pn.Row(
            dmap,                # [0]
            pn.Spacer(width=10), # [1]
            pn.Column(
                pn.Spacer(height=25), # [0]
                selectors,            # [1]
                init_plot,            # [2]
            )
        )

        # Show gui
        # print("gui layout:", self._gui_layout) # for debugging
        self._gui_layout.show(title=self._app_name, threaded=True)

# pylint: disable=too-many-locals
    def _update_plot(self, **kwargs):
        ''' Create plot with inputs from GUI.  Must return plot, even if empty plot, for DynamicMap.
            See binding for DynamicMap to see function arguments. '''
        gui_inputs = {**kwargs}
        print("***** _update_plot: inputs=", gui_inputs)

        if self._toast:
            self._toast.destroy()

        if not gui_inputs['ms']:
            # Launched GUI with no MS
            self._last_gui_plot = self._empty_plot
            return self._last_gui_plot

        if not gui_inputs['do_plot'] and self._last_gui_plot:
            # Not ready to update plot yet, return last plot
            return self._last_gui_plot

        # Extract style params
        self._set_style_params(gui_inputs)

        # Extract plot params
        plot_inputs = self._set_plot_inputs(gui_inputs)

        # If ms changed, update GUI with ms info
        if self._set_ms(gui_inputs['ms']) and self._data:
            self._update_gui_axis_options()

        # Do new plot
        self._reset_plot()
        gui_plot = None

        if not self._last_gui_plot or self._inputs_changed(plot_inputs):
            # First plot or changed plot
            try:
                # Check inputs from GUI then plot
                self._plot_inputs = gui_inputs
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

        self._last_gui_plot = gui_plot
        self._update_plot_spinner(False)
        return gui_plot
# pylint: disable=too-many-locals

    def _do_gui_plot(self):
        ''' Create plot based on gui plot inputs '''
        if self._data and self._data.is_valid():
            plot = None

            # Make iter plot (possibly with subplots layout)
            if self._plot_inputs['iter_axis']:
                self._do_iter_plot(self._plot_inputs)
                subplots = self._plot_inputs['subplots']
                layout_plot, is_layout = super()._layout_plots(subplots)

                if is_layout:
                    # Cannot show Layout in DynamicMap
                    super().show()
                    return self._last_gui_plot
                # Overlay raster plot for DynamicMap
                return layout_plot

            # Make single Overlay raster plot for DynamicMap
            plot, plot_params = self._do_plot(self._plot_inputs)
            self._update_color_range(plot_params) # Update color limits in gui if calculated for plot
            if plot_params['colorbar']['show']:   # Update colorbar titles with selected vis axis
                plot.QuadMesh.I = self._set_colorbar(plot.QuadMesh.I, plot_params, "flagged")
                plot.QuadMesh.II = self._set_colorbar(plot.QuadMesh.II, plot_params, "unflagged")

            return plot.opts(
                hv.opts.QuadMesh(tools=['hover'])
            )

        # Make single Overlay raster plot for DynamicMap
        return self._empty_plot

    def _create_empty_plot(self):
        ''' Create empty Overlay plot for DynamicMap with default color params and hover enabled '''
        plot_params = self._raster_plot.get_plot_params()
        plot = hv.Overlay(
            hv.QuadMesh([]).opts(
                colorbar=False,
                cmap=plot_params['flagged_cmap']
            ) * hv.QuadMesh([]).opts(
                colorbar=plot_params['colorbar']['show'],
                cmap=plot_params['unflagged_cmap']
            )
        )
        return plot.opts(
            hv.opts.QuadMesh(tools=['hover'])
        )

    def _set_colorbar(self, plot, plot_params, colorbar_key):
        ''' Update colorbar with c_label for vis_axis '''
        c_label = plot_params['data']['axis_labels']['c']['label']
        color_limits = plot_params['data']['color_limits']

        if plot_params['colorbar'][colorbar_key]:
            title = "Flagged " + c_label if colorbar_key == "flagged" else c_label
            plot = plot.opts(
                colorbar=True,
                backend_opts={
                    "colorbar.title": title,
                }
            )
            if color_limits:
                plot = plot.opts(
                    clim=color_limits,
                )
        else:
            plot = plot.opts(
                colorbar=False,
            )
            if color_limits:
                plot = plot.opts(
                    clim=color_limits,
                )
        return plot

    ###
    ### Access selectors
    ###
    def _get_selector(self, name):
        ''' Return selector group for name '''
        selectors = self._gui_layout[2][1]
        if name == "file":
            return selectors[0]
        if name == "title":
            return selectors[1]
        if name == "style":
            return selectors[2]
        if name == "axis":
            return selectors[3]
        if name == "agg":
            return selectors[4]
        if name == "iter":
            return selectors[5]
        raise ValueError(f"No selector for {name}")

    ###
    ### Update widget options based on MS
    ###
    def _update_gui_axis_options(self):
        ''' Set gui options from ms data '''
        if 'data_dims' in self._ms_info:
            data_dims = self._ms_info['data_dims']

            # Update options for x_axis and y_axis selectors
            axis_selectors = self._get_selector('axis')
            axis_selectors.objects[0][0].options = data_dims
            axis_selectors.objects[0][1].options = data_dims

            # Update options for vis_axis selector ([2])
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
    ### Widgets which update other widgets
    ###
    def _set_filename(self, filename):
        ''' Set filename in text box from file selector value (list) '''
        if filename and self._gui_layout:
            file_selectors = self._get_selector('file')

            # Collapse FileSelector card
            file_selectors[1].collapsed = True

            # Set filename from last file in file selector (triggers _update_plot())
            file_selectors[0][0].width = len(filename[-1])
            file_selectors[0][0].value = filename[-1]

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
        ''' Return list of float time values as list of datetime values '''
        time_attrs = self._data.get_dimension_attrs('time')
        datetime_values = []
        try:
            datetime_values = to_datetime(float_times, unit=time_attrs['units'], origin=time_attrs['format'])
        except TypeError:
            datetime_values = to_datetime(float_times, unit=time_attrs['units'][0], origin=time_attrs['format'])
        return list(datetime_values)

    def _update_color_range(self, plot_params):
        ''' Set the range on the colorbar to limits of plot '''
        if self._gui_layout and 'data' in plot_params:
            data_params = plot_params['data']
            data_min = data_params['data_min'] if 'data_min' in data_params else None
            data_max = data_params['data_max'] if 'data_max' in data_params else None
            color_limits = data_params['color_limits'] if 'color_limits' in data_params else None

            style_selectors = self._get_selector('style')
            range_slider = style_selectors[1][1]

            # Update range slider start and end if changed
            if (data_min and data_min != range_slider.start) or (data_max and data_max != range_slider.end):
                range_slider.start = data_min
                range_slider.end = data_max

            # Update range slider value if set else use min-max
            if color_limits:
                if color_limits != range_slider.value:
                    range_slider.value = color_limits
            else:
                range_slider.value = (data_min, data_max)

    def _update_plot_spinner(self, do_plot):
        ''' Start spinner when plot button value is True. '''
        if self._gui_layout:
            spinner = self._gui_layout[2][2][1]
            spinner.value = do_plot

    ###
    ### Process input values from widgets
    ###
    def _set_style_params(self, input_params):
        ''' Extract style parameters from input parameters and set for plot '''
        style_params = {}
        style_params['unflagged_cmap'] = input_params.pop('unflagged_cmap')
        style_params['flagged_cmap'] = input_params.pop('flagged_cmap')
        style_params['show_colorbar'] = input_params.pop('show_colorbar')
        self.set_style_params(**style_params)

    def _set_plot_inputs(self, gui_inputs):
        ''' Set plot inputs (only) from gui inputs in expected format such as tuples '''
        self._set_aggregation_inputs(gui_inputs)
        self._set_iteration_inputs(gui_inputs)

        # Set title to None if not set
        title = gui_inputs['title']
        gui_inputs['title'] = None if title == '' else title

        # Set subplots tuple
        rows = gui_inputs.pop('subplot_rows')
        columns = gui_inputs.pop('subplot_columns')
        gui_inputs['subplots'] = None if rows == 1 and columns ==1 else (rows, columns)

        # If auto box checked, do not use gui color range
        auto_color_limits = gui_inputs.pop('auto_color_limits')
        if auto_color_limits:
            gui_inputs['color_limits'] = None

        # Extract plot inputs
        plot_inputs = {}
        for key in gui_inputs:
            if key in self._plot_inputs:
                plot_inputs[key] = gui_inputs[key]
        return plot_inputs

    def _set_aggregation_inputs(self, inputs):
        ''' Set aggregator and agg_axis to None if not set '''
        aggregator = inputs['aggregator']
        inputs['aggregator'] = None if aggregator == 'None' else aggregator

        if aggregator:
            agg_axis = inputs['agg_axis']
            inputs['agg_axis'] = None if agg_axis == [] else agg_axis
        else:
            inputs['agg_axis'] = None

    def _set_iteration_inputs(self, inputs):
        ''' Set input iteration axis, and range if iter_axis is set. '''
        iter_axis = inputs['iter_axis']
        iter_axis = None if iter_axis == 'None' else iter_axis
        inputs['iter_axis'] = iter_axis

        if iter_axis:
            iter_value_type = inputs['iter_value_type']

            if iter_value_type == 'Value':
                # Use index of iter_value for tuple
                iter_val = inputs.pop('iter_value')
                if iter_val and self._data and self._data.is_valid():
                    iter_values = self._data.get_dimension_values(iter_axis)
                    iter_index = iter_values.index(iter_val)
                    inputs['iter_range'] = (iter_index, iter_index)
            else:
                # Use range start and end values for tuple
                start = inputs.pop('iter_range_start')
                end = inputs.pop('iter_range_end')
                inputs['iter_range'] = (start, end)
        else:
            inputs['iter_range'] = None

    def _inputs_changed(self, plot_inputs):
        ''' Check if inputs changed and need new plot '''
        # Cannot use plot_inputs == self._plot_inputs until selection in GUI
        for key in plot_inputs:
            if plot_inputs[key] and self._plot_inputs[key]: # Both set
                if plot_inputs[key] != self._plot_inputs[key]:
                    return True
            elif not plot_inputs[key] and not self._plot_inputs[key]: # Both not set
                continue
            elif key != 'color_limits':
                # One is None, other is set. Ignore color limits inequality since calculated when None.
                return True
        return False
