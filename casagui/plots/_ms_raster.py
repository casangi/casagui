'''
Implementation of the ``VisRaster`` application for plotting and editing
visibilities
'''

import os
import time

from graphviper.utils.logger import setup_logger

from ..data.measurement_set._ms_data import is_vis_axis, get_correlated_data
from ..data.measurement_set._raster_data import raster_data
from ..data.measurement_set._ms_stats import calculate_ms_stats 
from ..data.measurement_set._xds_utils import set_baseline_coordinate
from ..io._ms_io import get_processing_set
from ..plot import raster_plot
from ..plots._ms_plot import print_summary, get_data_groups, list_data_groups, list_antennas, show, save

class MSRaster:
    '''
    Plot MeasurementSet data as raster plot.

    Args:
        ms (str): path in MSv2 (.ms) or MSv4 (.zarr) format.
        log_level (str): logging threshold, default 'INFO'

    Example:
        msr = MSRaster(vis='myvis.ms')
        msr.summary()
        msr.plot(x_axis='baseline_id', y_axis='time', vis_axis='amp') # default, same as msr.plot() with no arguments
        msr.show()
        msr.save() # saves as {ms name}_raster.png
    '''

    def __init__(self, ms, log_level="INFO"):
        # Logger
        self._logger = setup_logger(logger_name="MSRaster", log_to_term=True, log_to_file=False, log_level=log_level)

        # Processing set
        self._ps, self._ms_path = get_processing_set(ms)

        # ms name (no path) for plot title and save filename
        self._ms_basename = os.path.splitext(os.path.basename(self._ms_path))[0]

        n_datasets = len(self._ps)
        if n_datasets == 0:
            raise RuntimeError("Failed to read visibility file into processing set")
        self._logger.info(f"Processing set contains {n_datasets} msv4 datasets.")

        for name, xds in self._ps.items():
            if 'baseline_id' in xds.coords:
                self._ps[name] = set_baseline_coordinate(xds)

        self._spw_color_limits = {}
        self._plot = None


    def summary(self, columns=None):
        ''' Print processing set summary.
            Args: columns (None, str, list): type of metadata to list.
                None:      Print all summary columns in processing set.
                'by_msv4': Print formatted summary metadata per MSv4.
                str, list: Print a subset of summary columns in processing set.
                           Options include 'name', 'intents', 'shape', 'polarization', 'scan_number', 'spw_name', 'field_name', 'source_name', 'line_name', 'field_coords', 'start_frequency', 'end_frequency'
        '''
        print_summary(self._ps, columns)

    def list_data_groups(self):
        ''' List names of data groups (set of related correlated data, flag, weight, and uvw) in processing set '''
        list_data_groups(self._ps, self._logger)

    def list_antennas(self, plot_positions=False):
        '''
            List names of antennas in processing set.
            plot_positions (bool): plot antenna positions Y vs X, Z vs X, Z vs Y.  Default False.
                Exit each scatter plot (or press q) to advance to next plot then return to console.
        '''
        list_antennas(self._ps, self._logger, plot_positions)

    def plot_phase_centers(self, label_all_fields=False, data_group='base'):
        '''
            Plot the phase center locations of all fields in the Processing Set.
            See https://xradio.readthedocs.io/en/latest/measurement_set/tutorials/ps_vis.html#PS-Structure
            Exit plot (or press q) to return to console.
        '''
        self._ps.plot_phase_centers(label_all_fields, data_group)

    def plot(self, x_axis='baseline', y_axis='time', vis_axis='amp', data_group='base', selection=None, showgui=False):
        '''
        Create a raster plot of vis_axis data in the data_group after applying selection.
        Plot axes include data dimensions (time, baseline/antenna, frequency, polarization).
        Dimensions not set as plot axes can be selected, else the first will be used.

        Args:
            x_axis (str): Plot x-axis. Default 'baseline' ('antenna_name' for spectrum data).
            y_axis (str): Plot y-axis. Default 'time'.
            vis_axis (str): Complex visibility component to plot (amp, phase, real, imag). Default 'amp'.
            data_group (str): xds data group name of correlated data, flags, weights, and uvw.  Default 'base'.
                Use list_data_groups() to see options.
            selection (dict): selected data to plot. Options include:
                Processing set selection:
                    'name', 'intents', 'shape', 'polarization', 'scan_number', 'spw_name', 'field_name', 'source_name', 'field_coords', 'start_frequency', 'end_frequency': select by summary() column names
                    'query': for pandas query of summary() columns.
                    Default: select first spw (first by id).
                Dimension selection:
                    Visibilities: 'baseline' 'time', 'frequency', 'polarization'
                    Spectrum: 'antenna_name', 'time', 'frequency', 'polarization'
                    Default is index 0 for non-axes dimensions.
                    Use list_antennas() for antenna names. Select 'baseline' as "<name1> & <name2>".
                    Use summary() to list frequencies and polarizations.
                    TODO: how to select time?
            showgui (bool): whether to launch interactive GUI in browser. Default False.

        If not showgui and plotting is successful, use show() or save() to view/save the plot only.
        '''
        start = time.time()

        # Validate input arguments
        x_axis, y_axis = self._check_plot_inputs(x_axis, y_axis, vis_axis, data_group, selection)

        # Apply selection to processing set
        selected_ps, selection = self._select_ps(selection, x_axis, y_axis, data_group)
        self._logger.info(f"Plotting {len(selected_ps)} msv4 datasets.")
        self._logger.debug(f"Processing set maximum dimensions: {selected_ps.get_ps_max_dims()}")

        # For amplitude, limit colorbar range using ms stats
        color_limits = None
        if vis_axis == 'amp':
            selected_spw = selection['spw_name']
            if selected_spw in self._spw_color_limits:
                color_limits = self._spw_color_limits[selected_spw]
            else:
                color_limits = self._calc_amp_color_limits(selected_ps, data_group)
                self._spw_color_limits[selected_spw] = color_limits
        if color_limits is None:
            self._logger.info("Autoscale colorbar limits")
        else:
            self._logger.info(f"Setting colorbar limits: ({color_limits[0]:.4f}, {color_limits[1]:.4f}).")

        # Select data and concat into xarray Dataset for raster plot
        raster_xds, selection = raster_data(selected_ps, x_axis, y_axis, vis_axis, data_group, selection, self._logger)

        # Plot selected xds
        if showgui:
            raise RuntimeError("Interactive GUI not implemented.")
        else:
            ms_name = os.path.basename(self._ms_path)
            self._plot = raster_plot(raster_xds, x_axis, y_axis, vis_axis, data_group, selection, ms_name, color_limits)
            if self._plot is None:
                raise RuntimeError("Plot failed.")

        self._logger.debug(f"Plot elapsed time: {time.time() - start:.2f}s.")

    def show(self):
        ''' 
        Show interactive Bokeh plot in a browser.
        Plot tools include pan, zoom, hover, and save.
        '''
        if self._plot is None:
            raise RuntimeError("No plot to show.")

        title="MSRaster " + self._ms_basename
        show(self._plot, title)

    def save(self, filename='', fmt='auto', hist=False, backend='bokeh', resources='online', toolbar=None, title=None):
        '''
        Save plot to file.
            filename (str): Name of file to save. Default '': see below.
            fmt (str): Format of file to save ('png', 'svg', 'html', or 'gif'). Default 'auto': inferred from filename.
            hist (bool): Whether to compute and adjoin histogram.  Default False.
            backend (str): rendering backend, 'bokeh' or 'matplotlib'.  Default None = 'bokeh'.
            resources (str): whether to save with 'online' or 'offline' resources.  'offline' creates a larger file. Default 'online'.
            toolbar (bool, None): Whether to include the toolbar in the exported plot (True) or not (False). Default None: display the toolbar unless plotfile is png.
            title (str): Custom title for exported HTML file.

        If filename is set, the plot will be exported to the specified filename in the format of its extension (see fmt options).  If not set, the plot will be saved as a PNG with name {vis}_raster.png.

        '''
        if self._plot is None:
            raise RuntimeError("No plot to save.")

        start = time.time()
        if not filename:
            filename = f"{self._ms_basename}_raster.png"
        save(self._plot, filename, fmt, hist, backend, resources, toolbar, title)
        self._logger.info(f"Saved plot to {filename}.")
        self._logger.debug(f"Save elapsed time: {time.time() - start:.3f} s.")


    def _check_plot_inputs(self, x_axis, y_axis, vis_axis, data_group, selection):
        ''' Check plot parameters against processing set xds variables '''
        if data_group not in get_data_groups(self._ps):
            raise ValueError(f"Invalid data_group {data_group}. Use list_data_groups() to see options.")

        # Reassign x_axis or y_axis for spectrum data dimension
        correlated_data = get_correlated_data(self._ps.get(0), data_group)
        x_axis = "antenna_name" if x_axis == "baseline" and correlated_data == "SPECTRUM" else x_axis
        y_axis = "antenna_name" if y_axis == "baseline" and correlated_data == "SPECTRUM" else y_axis

        valid_axes = list(self._ps.get(0)[correlated_data].dims)
        if x_axis not in valid_axes or y_axis not in valid_axes:
            raise ValueError(f"Invalid x or y axis, please select from {valid_axes}")

        if not is_vis_axis(vis_axis):
            raise ValueError(f"Invalid vis_axis {vis_axis}")

        if selection and not isinstance(selection, dict):
            # TODO: check keys?
            raise RuntimeError("selection must be dictionary")

        return x_axis, y_axis


    def _select_ps(self, selection, x_axis, y_axis, data_group):
        ''' Apply ps selection: spw_name, field_name, source_name, intents '''
        selected_ps = self._ps

        # Apply user selection
        if selection:
            ps_selection = {}
            ps_selection_keys = self._ps.summary().columns
            for key in selection:
                if key in ps_selection_keys:
                    ps_selection[key] = selection[key]
            if ps_selection:
                self._logger.info(f"Applying user selection to processing set: {ps_selection}")
                selected_ps = self._ps.sel(**ps_selection)

        # Select first spw (min id) if not user-selected
        if not selection or 'spw_name' not in selection:
            first_spw_name = self._get_first_spw_name(selected_ps)
            spw_selection = {'spw_name': first_spw_name}
            selected_ps = selected_ps.sel(**spw_selection)
            # Add spw selection to selection
            selection = selection | spw_selection if selection else spw_selection

        # Select data group
        for name, ms_xds in selected_ps.items():
            selected_ps[name] = ms_xds.sel(data_group_name=data_group)
        return selected_ps, selection


    def _get_first_spw_name(self, ps):
        ''' Return spw selection by name (str or list) or first by frequency if selection is None '''
        # Collect spw names by id
        spw_id_names = {}
        for key in ps:
            freq_xds = ps[key].frequency
            spw_id_names[freq_xds.spectral_window_id] = freq_xds.spectral_window_name

        # spw not selected: select first spw by id and return name
        first_spw_id = min(spw_id_names)
        first_spw_name = spw_id_names[first_spw_id]

        # describe selected spw
        spw_df = ps.summary()[ps.summary()['spw_name'] == first_spw_name]
        self._logger.info(f"Selecting first spw id {first_spw_id}: {first_spw_name} with range {spw_df.at[spw_df.index[0], 'start_frequency']:e} - {spw_df.at[spw_df.index[0], 'end_frequency']:e}")
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
