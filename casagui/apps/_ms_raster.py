'''
Implementation of the ``MsRaster`` application for measurement set raster plotting and editing
'''

import os
import time

from casagui.plots._ms_plot import MsPlot
from casagui.data.measurement_set._ms_data import is_vis_axis, get_correlated_data, get_dimension_values
from casagui.data.measurement_set._ms_select import select_ps 
from casagui.data.measurement_set._ms_stats import calculate_ms_stats 
from casagui.data.measurement_set._raster_data import raster_data
from casagui.plot import raster_plot_params, raster_plot

class MsRaster(MsPlot):
    '''
    Plot MeasurementSet data as raster plot.

    Args:
        ms (str): path in MSv2 (.ms) or MSv4 (.zarr) format.
        log_level (str): logging threshold'. Options include "debug", "info", "warning", "error", "critical". Default "info".
        interactive (bool): whether to launch interactive GUI in browser. Default False.

    Example:
        from casagui.plots import MsRaster
        msr = MsRaster(vis='myvis.ms')
        msr.summary()
        msr.plot(x_axis='frequency', y_axis='time', vis_axis='amp', data_group='base')
        msr.show()
        msr.save() # saves as {ms name}_raster.png
    '''

    def __init__(self, ms, log_level="info", interactive=False):
        super().__init__(ms, log_level, "MsRaster", interactive)
        if interactive:
            self._logger.warn("Interactive GUI not implemented.")
            self._interactive = False
        self._spw_color_limits = {}

    def plot(self, x_axis='baseline', y_axis='time', vis_axis='amp', data_group='base', selection=None, aggregator=None, agg_axis=None, iter_axis= None, title=None, clear_plots=True):
        '''
        Create a raster plot of vis_axis data in the data_group after applying selection.
        Plot axes include data dimensions (time, baseline/antenna, frequency, polarization).
        Dimensions not set as plot axes can be selected, else the first value will be used, unless aggregated.

        Args:
            x_axis (str): Plot x-axis. Default 'baseline' ('antenna_name' for spectrum data).
            y_axis (str): Plot y-axis. Default 'time'.
            vis_axis (str): Complex visibility component to plot (amp, phase, real, imag). Default 'amp'.
            data_group (str): xds data group name for correlated data, flags, weights, and uvw.  Default 'base'.
                Call data_groups() to see options.
            selection (dict): selected data to plot. Options include:
                Processing Set selection: by summary column names. Call summary() to see options.
                    'query': for pandas query of summary() columns.
                    Default: select first spw (by id).
                Dimension selection:
                    Visibilities: 'baseline' 'time', 'frequency', 'polarization'
                    Spectrum: 'antenna_name', 'time', 'frequency', 'polarization'
                    Default is index 0 for non-axes dimensions.
                    Call antennas() for antenna names. Select 'baseline' as "<name1> & <name2>".
                    Call summary() to list frequencies and polarizations.
                    TODO: how to select time?
            aggregator (str): reduction for rasterization. Default None.
                Options include 'max', 'mean', 'min', 'std', 'sum', 'var'.
            agg_axis (str, list): which dimension to apply aggregator across. Default None.
                Options include one or more dimensions. Non-agg dimension will be selected.
                If agg_axis is None and aggregator is set, aggregates over all non-axis dimensions.
            iter_axis (str): dimension over which to iterate values (starting at layout start).
            title (str): Plot title, default None (generate title from ms and selection).
            clear_plots (bool): whether to clear list of plots.

        If not interactive and plotting is successful, use show() or save() to view/save the plot only.
        '''
        start = time.time()
        if clear_plots:
            super().clear_plots()

        # Validate input arguments
        x_axis, y_axis, agg_axis = self._check_plot_inputs(x_axis, y_axis, vis_axis, data_group, selection, aggregator, agg_axis, iter_axis)

        # Apply selection to processing set (select spw before calculating colorbar limits)
        if selection:
            selected_ps = self._do_user_ps_selection(selection)
        else:
            selected_ps = self._ps
            selection = {}

        if 'spw_name' not in selection:
            selected_ps, selection = self._select_first_spw(selected_ps, selection)
        self._logger.info(f"Plotting {len(selected_ps)} msv4 datasets.")
        self._logger.info(f"Maximum dimensions for selected spw: {selected_ps.get_ps_max_dims()}")

        # Colorbar limits if not interactive (user can adjust interactively)
        color_limits = None
        if not self._interactive and not aggregator and vis_axis == 'amp':
            # For amplitude, limit colorbar range using ms stats
            spw_name = selection['spw_name']
            if spw_name in self._spw_color_limits:
                color_limits = self._spw_color_limits[spw_name]
            else:
                color_limits = self._calc_amp_color_limits(selected_ps, data_group)
                self._spw_color_limits[spw_name] = color_limits
        if color_limits:
            self._logger.info(f"Setting colorbar limits: ({color_limits[0]:.4f}, {color_limits[1]:.4f}).")
        else:
            self._logger.info("Autoscale colorbar limits")

        if iter_axis:
            iter_values = get_dimension_values(selected_ps, iter_axis)
            for value in iter_values:
                # Select iteration value and make plot
                self._logger.info(f"Plot {iter_axis} iteration value {value}")
                selection[iter_axis] = value
                self._do_plot(selected_ps, x_axis, y_axis, vis_axis, data_group, selection, aggregator, agg_axis, title, color_limits)
        else:
            self._do_plot(selected_ps, x_axis, y_axis, vis_axis, data_group, selection, aggregator, agg_axis, title, color_limits)

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
        if not title:
            title="MsRaster " + self._ms_basename
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
            filename = f"{self._ms_basename}_raster.png"
        super().save(filename, fmt, layout, export_range)

    def _check_plot_inputs(self, x_axis, y_axis, vis_axis, data_group, selection, aggregator, agg_axis, iter_axis):
        ''' Check plot parameters against processing set xds variables '''
        if data_group not in self.data_groups():
            raise ValueError(f"Invalid data_group {data_group}. Use get_data_groups() to see options.")

        # Rename "baseline" x_axis or y_axis for SPECTRUM data dimension
        correlated_data = get_correlated_data(self._ps.get(0), data_group)
        x_axis = 'antenna_name' if x_axis == 'baseline' and correlated_data == "SPECTRUM" else x_axis
        y_axis = 'antenna_name' if y_axis == 'baseline' and correlated_data == "SPECTRUM" else y_axis

        data_dims = list(self._ps.get(0)[correlated_data].dims)
        if x_axis not in data_dims or y_axis not in data_dims:
            raise ValueError(f"Invalid x or y axis, please select from {data_dims}.")

        if not is_vis_axis(vis_axis):
            raise ValueError(f"Invalid vis_axis {vis_axis}.")

        if selection and not isinstance(selection, dict):
            raise RuntimeError("Invalid selection: must be dictionary.")

        valid_aggs = ['max', 'mean', 'min', 'std', 'sum', 'var']
        if aggregator and aggregator not in valid_aggs:
            raise RuntimeError(f"Invalid aggregator {aggregator}. Options include {valid_aggs}.")

        if aggregator and not agg_axis:
            agg_axis = data_dims
            agg_axis.remove(x_axis)
            agg_axis.remove(y_axis)

        if agg_axis:
            if not isinstance(agg_axis, list) and not isinstance(agg_axis, str):
                raise RuntimeError(f"Invalid agg axis {agg_axis}. Options include one or more dimensions {data_dims}.")
            if isinstance(agg_axis, str):
                agg_axis = [agg_axis]
            for axis in agg_axis:
                if axis not in data_dims or axis in (x_axis, y_axis):
                    raise RuntimeError(f"Invalid aggregator axis {axis}. Must be dimension which is not a plot axis.")

        if iter_axis and (iter_axis in (x_axis, y_axis) or iter_axis not in data_dims):
            raise RuntimeError(f"Invalid aggregator axis {axis}. Must be dimension which is not a plot axis.")
        if iter_axis and (iter_axis not in data_dims or iter_axis in (x_axis, y_axis)):
            raise RuntimeError(f"Invalid iteration axis {iter_axis}. Must be dimension which is not a plot axis.")

        return x_axis, y_axis, agg_axis

    def _do_user_ps_selection(self, selection):
        if not selection:
            return self._ps

        # Select summary columns or by query
        ps_selection = {}
        summary_columns = self._ps.summary().columns
        for key in selection:
            if key == 'query' or key in summary_columns:
                ps_selection[key] = selection[key]
        return self._ps.sel(**ps_selection)
  
    def _select_first_spw(self, ps, selection):
        ''' Select first spw (minimum spectral_window_id) if not user-selected '''
        first_spw_name = self._get_first_spw_name()
        spw_selection = {'spw_name': first_spw_name}
        selected_ps = ps.sel(**spw_selection)

        # Add to selection for plot title
        selection = selection | spw_selection if selection else spw_selection
        return selected_ps, selection

    def _get_first_spw_name(self):
        ''' Return first spw id name '''
        # Collect spw names by id
        spw_id_names = {}
        for xds in self._ps.values():
            freq_xds = xds.frequency
            spw_id_names[freq_xds.spectral_window_id] = freq_xds.spectral_window_name

        # spw not selected: select first spw by id and return name
        first_spw_id = min(spw_id_names)
        first_spw_name = spw_id_names[first_spw_id]

        # describe selected spw
        spw_df = self._ps.summary()[self._ps.summary()['spw_name'] == first_spw_name]
        self._logger.info(f"Selecting first spw id {first_spw_id} with frequency range {spw_df.at[spw_df.index[0], 'start_frequency']:e} - {spw_df.at[spw_df.index[0], 'end_frequency']:e}")
        return first_spw_name

    def _calc_amp_color_limits(self, ps, data_group):
        # Calculate colorbar limits from amplitude stats for unflagged data
        self._logger.info("Calculating stats for colorbar limits.")
        start = time.time()
        min_val, max_val, mean, std = calculate_ms_stats(ps, self._ms_path, 'amp', data_group, self._logger)

        data_min = min(0.0, min_val)
        clip_min = max(data_min, mean - (3.0 * std))
        data_max = max(0.0, max_val)
        clip_max = min(data_max, mean + (3.0 * std))

        if clip_min == 0.0 and clip_max == 0.0:
            color_limits = None # flagged plot
        else:
            color_limits = (clip_min, clip_max)
        self._logger.debug(f"Stats elapsed time: {time.time() - start:.2f} s.")
        return color_limits

    def _do_plot(self, ps, x_axis, y_axis, vis_axis, data_group, selection, aggregator, agg_axis, title, color_limits):
        # Select data and concat into xarray Dataset for raster plot
        plot_data, selection = raster_data(ps, x_axis, y_axis, vis_axis, data_group, selection, aggregator, agg_axis, self._logger)

        # Get options needed for plot
        plot_params = raster_plot_params(plot_data, x_axis, y_axis, vis_axis, data_group, selection, title, self._ms_basename, color_limits, aggregator)

        if self._interactive:
            pass # send data to gui
        else:
            plot = raster_plot(plot_data, plot_params)
            if plot is None:
                raise RuntimeError("Plot failed.")
            self._plots.append(plot)
