'''
Implementation of the ``MsRaster`` application for measurement set raster plotting and editing
'''

import time

import holoviews as hv
import numpy as np
import panel as pn

from casagui.bokeh.state._palette import available_palettes
from casagui.plot._ms_plot import MsPlot
from casagui.plot._ms_plot_constants import VIS_AXIS_OPTIONS, SPECTRUM_AXIS_OPTIONS, PLOT_WIDTH, PLOT_HEIGHT
from casagui.plot._panel_selectors import file_selector, title_selector, style_selector, axis_selector, aggregation_selector, iteration_selector
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
            # Make sure gui update is not triggered before fully created
            self._gui_layout = None

            # Set default plot inputs only using plot(); raster plot is triggered by gui
            self.plot()

            # Set default plot style inputs
            self.set_style_params()

            self._launch_gui()

            # Set filename TextInput to trigger plot of this MS
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

        # Get params needed for plot, such as title, labels, and ticks
        plot_inputs['color_limits'] = self._get_color_limits(plot_inputs)
        plot_inputs['ms_name'] = self._ms_info['basename'] # for title
        self._raster_plot.set_data_params(raster_data, plot_inputs)

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

        # Put user input widgets in accordion with only one card active at a time
        selectors = pn.Accordion(
            ("Select file", file_selectors), # [0]
            ("Plot title", title_input),     # [1]
            ("Plot style", style_selectors), # [2]
            ("Plot axes", axis_selectors),   # [3]
            ("Aggregation", agg_selectors),  # [4]
            ("Iteration", iter_selectors),   # [5]
        )
        selectors.toggle = True

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
            iter_axis=iter_selectors[0],
            iter_value=iter_selectors[1],
        )).opts(
            width=PLOT_WIDTH, height=PLOT_HEIGHT
        )

        # Layout plot and widget box in a row
        self._gui_layout = pn.Row(
            dmap,                # [0]
            pn.Spacer(width=10), # [1]
            selectors,           # [2]
        )

        # Show gui
        # print("gui layout:", self._gui_layout) # for debugging
        self._gui_layout.show(title=self._app_name, threaded=True)

# pylint: disable=too-many-arguments, too-many-positional-arguments, too-many-locals, unused-argument
    def _update_plot(
        self, ms, title, unflagged_cmap, flagged_cmap, show_colorbar, auto_color_limits, color_limits, x_axis, y_axis, vis_axis, aggregator, agg_axis, iter_axis, iter_value):
        ''' Create plot with inputs from GUI if possible.  Must return plot for DynamicMap. '''
        update_inputs = locals()

        # Add to iteration card in gui
        update_inputs['iter_range'] = None
        update_inputs['subplots'] = None
        # Add selection card in gui
        update_inputs['selection'] = None

        # print("_update_plot inputs:", update_inputs)
        if self._toast:
            self._toast.destroy()
        self._reset_plot()

        if not ms:
            # Launched GUI with no MS
            return self._empty_plot()

        # If ms changed, update GUI with ms info
        if self._set_ms(ms) and self._data:
            self._update_gui_options()

        update_inputs['aggregator'] = None if aggregator == "None" else aggregator
        update_inputs['iter_axis'] = None if iter_axis == 'None' else iter_axis
        if auto_color_limits:
            update_inputs['color_limits'] = None

        # Style params
        style_params = self._set_style_params(update_inputs)
        self.set_style_params(**style_params)

        try:
            # Update inputs from GUI and check values (also update baseline axis if needed)
            self._plot_inputs = update_inputs
            self._plot_inputs['data_dims'] = self._ms_info['data_dims']
            check_inputs(self._plot_inputs)
            self._init_plot(self._plot_inputs) # before adding iter selection

            # Iteration params
            iter_selection = self._set_iter_selection(update_inputs)
            if iter_selection:
                if self._plot_inputs['selection']:
                    self._plot_inputs['selection'] |= iter_selection
                else:
                    self._plot_inputs['selection'] = iter_selection
        except (ValueError, TypeError) as e:
            self._notify(str(e), 'error', 0)
            return self._empty_plot()

        return self._do_gui_plot()
# pylint: enable=too-many-arguments, too-many-positional-arguments, too-many-locals, unused-argument

    def _do_gui_plot(self):
        if self._data and self._data.is_valid():
            try:
                # Make raster plot and return to GUI
                plot, plot_params = self._do_plot(self._plot_inputs)
                # Update color limits range if calculated for plot
                self._update_color_range(plot_params)

                # Update colorbar titles with selected vis axis
                if plot_params['colorbar']['show']:
                    plot.QuadMesh.I = self._set_colorbar(plot.QuadMesh.I, plot_params, "flagged")
                    plot.QuadMesh.II = self._set_colorbar(plot.QuadMesh.II, plot_params, "unflagged")

                return plot.opts(
                    hv.opts.QuadMesh(tools=['hover'])
                )
            except RuntimeError as e:
                self._notify(str(e), 'error', 0)
        return self._empty_plot()

    def _empty_plot(self):
        ''' Return empty plot with plot_params and hover enabled '''
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

    def _update_gui_options(self):
        ''' Set gui options from ms data '''
        if 'data_dims' in self._ms_info:
            data_dims = self._ms_info['data_dims']
            axis_selectors = self._gui_layout[2].objects[3]
            agg_selectors = self._gui_layout[2].objects[4]
            iter_selectors = self._gui_layout[2].objects[5]

            # Update options for x_axis and y_axis selectors
            axis_selectors.objects[0][0].options = data_dims
            axis_selectors.objects[0][1].options = data_dims

            # Update options for vis_axis selector ([2])
            if self._data.get_correlated_data('base') == 'SPECTRUM':
                axis_selectors.objects[1].options = SPECTRUM_AXIS_OPTIONS
            else:
                axis_selectors.objects[1].options = VIS_AXIS_OPTIONS

            # Update options for agg axes selector
            agg_selectors[1].options = data_dims

            # Update options for iteration axis selector
            iter_selectors[0].options = ['None']
            iter_selectors[0].options.extend(data_dims)

    ###
    ### Widgets which update other widgets
    ###
    def _set_filename(self, filename):
        ''' Set filename in text box from file selector value (list) '''
        if filename and self._gui_layout:
            file_selectors = self._gui_layout[2].objects[0]
            # Collapse file selector card
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
                iter_value_player = self._gui_layout[2].objects[5][1]
                iter_value_player.options = iter_values
                iter_value_player.value = iter_values[0]
                iter_value_player.show_value = True

    def _update_color_range(self, plot_params):
        ''' Set the range on the colorbar to min max of plot data '''
        if self._gui_layout and 'data' in plot_params:
            data_params = plot_params['data']
            data_min = data_params['data_min'] if 'data_min' in data_params else None
            data_max = data_params['data_max'] if 'data_max' in data_params else None
            color_limits = data_params['color_limits'] if 'color_limits' in data_params else None

            style_selectors = self._gui_layout[2].objects[2]
            range_slider = style_selectors[1][1]

            # Update range slider if changed
            if (data_min and data_min != range_slider.start) or (data_max and data_max != range_slider.end):
                range_slider.start = data_min
                range_slider.end = data_max
                if (color_limits and color_limits != range_slider.value):
                    range_slider.value = color_limits
                else:
                    range_slider.value = (data_min, data_max)

    def _set_style_params(self, input_params):
        ''' Extract style parameters from input parameters '''
        style_params = {}
        style_params['unflagged_cmap'] = input_params.pop('unflagged_cmap')
        style_params['flagged_cmap'] = input_params.pop('flagged_cmap')
        style_params['show_colorbar'] = input_params.pop('show_colorbar')
        return style_params

    def _set_iter_selection(self, input_params):
        ''' Extract iteration parameters from input parameters and return selection dict. '''
        iter_selection = None
        if input_params['iter_axis']:
            iter_val = input_params.pop('iter_value')
            if iter_val:
                iter_selection = {input_params['iter_axis']: iter_val}
        return iter_selection
