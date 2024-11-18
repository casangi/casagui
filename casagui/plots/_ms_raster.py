'''
Implementation of the ``VisRaster`` application for plotting and editing
visibilities
'''

import os
import time

from graphviper.utils.logger import setup_logger

from ..data.measurement_set._ms_data import is_vis_spectrum_axis, get_vis_spectrum_data_var
from ..data.measurement_set._raster_data import raster_data
from ..data.measurement_set._ms_stats import calculate_ms_stats 
from ..data.measurement_set._ps_utils import summary
from ..data.measurement_set._xds_utils import set_coordinates
from ..io._ms_io import get_processing_set
from ..plot import raster_plot
from ..plots._ms_plot import show, save

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

        # Set baseline names and units for plotting
        for key in self._ps:
            self._ps[key] = set_coordinates(self._ps[key])

        self._spw_color_limits = {}
        self._plot = None


    def summary(self, columns=None):
        ''' Print processing set summary.
            Args: columns (None, str, list): type of metadata to list.
                None:      Print all summary columns in processing set.
                'by_msv4': Print formatted summary metadata per MSv4.
                str, list: Print a subset of summary columns in processing set.
                           Options include 'name', 'obs_mode', 'shape', 'polarization', 'spw_name', 'field_name', 'source_name', 'field_coords', 'start_frequency', 'end_frequency'
        '''
        summary(self._ps, columns)


    def plot(self, x_axis='baseline', y_axis='time', vis_axis='amp', selection=None, showgui=False):
        '''
        Create a static y_axis vs x_axis raster plot of visibility/spectrum data after applying selection.
        Plot axes include time, baseline/antenna, channel, and polarization. Axes not set as plot axes can be selected, else the first will be used.

        Args:
            x_axis (str): Plot x-axis. Default 'baseline' ('antenna' for spectrum).
            y_axis (str): Plot y-axis. Default 'time'.
            vis_axis (str): Visibility component (amp, phase, real, imag) and type if not data (corrected, model), e.g. 'phase_corrected'. Default 'amp'.
            selection (dict): selected data to plot. Options include:
              Processing set selection:
                Summary column names: 'name', 'obs_mode', 'shape', 'polarization', 'spw_name', 'field_name', 'source_name', 'field_coords', 'start_frequency', 'end_frequency'
                'query': for pandas query of summary columns.
                Default: select first spw by id.
              Plot selection:
                time, baseline, frequency, polarization: select data dimensions which are not plot axes. Default is index 0.
            showgui (bool): whether to launch interactive GUI

        If not showgui and plotting is successful, use show() or save() to view/save the plot only.
        '''
        start = time.time()
        self._check_plot_inputs(x_axis, y_axis, vis_axis, selection)

        # Apply metadata selection to processing set (spw, field, source, obs_mode)
        selected_ps, selection = self._select_ps(self._ps, selection, x_axis, y_axis)

        self._logger.info(f"Plotting {len(selected_ps)} msv4 datasets.")
        self._logger.debug(f"Processing set maximum dimensions: {selected_ps.get_ps_max_dims()}")

        # For amplitude, limit colorbar range using ms stats
        color_limits = None
        if 'amp' in vis_axis:
            selected_spw = selection['spw_name']
            if selected_spw in self._spw_color_limits:
                color_limits = self._spw_color_limits[selected_spw]
            else:
                color_limits = self._calc_amp_color_limits(selected_ps, vis_axis)
                self._spw_color_limits[selected_spw] = color_limits
            if color_limits is None:
                self._logger.info("Autoscale colorbar limits")
            else:
                self._logger.info(f"Setting colorbar limits: ({color_limits[0]:.4f}, {color_limits[1]:.4f}).")

        # Select data and concat into xarray Dataset for raster plot
        raster_xds, selection = raster_data(selected_ps, x_axis, y_axis, vis_axis, selection, self._logger)

        # Plot selected xds
        if showgui:
            raise RuntimeError("Interactive GUI not implemented.")
        else:
            self._plot = raster_plot(raster_xds, x_axis, y_axis, vis_axis, selection, self._ms_path, color_limits, self._logger)
            self._logger.debug(f"Plot elapsed time: {time.time() - start:.2f}s.")

            if self._plot is None:
                raise RuntimeError("Plot failed.")


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


    def _check_plot_inputs(self, x_axis, y_axis, vis_axis, selection):
        if not is_vis_spectrum_axis(vis_axis):
            raise ValueError(f"Invalid vis_axis {vis_axis}")

        data_var = get_vis_spectrum_data_var(self._ps, vis_axis)
        valid_axes = list(self._ps.get(0)[data_var].dims)
        if "SPECTRUM" in data_var:
            valid_axes.append('baseline') # has 'antenna_name' dim instead

        if x_axis not in valid_axes or y_axis not in valid_axes:
            raise ValueError(f"Invalid x or y axis, please select from {valid_axes}")

        if selection and not isinstance(selection, dict):
            raise RuntimeError("selection must be dictionary")


    def _select_ps(self, ps, selection, x_axis, y_axis):
        ''' Apply ps selection: spw_name, field_name, source_name, obs_mode '''
        selected_ps = ps

        # Apply user selection
        if selection:
            ps_selection = {}
            if 'spw_name' in selection:
                ps_selection['spw_name'] = selection['spw_name']
            if 'field_name' in selection:
                ps_selection['field_name'] = selection['field_name']
            if 'source_name' in selection:
                ps_selection['source_name'] = selection['source_name']
            if 'obs_mode' in selection:
                ps_selection['obs_mode'] = selection['obs_mode']
            if ps_selection:
                self._logger.info(f"Applying user selection to processing set: {ps_selection}")
                selected_ps = ps.sel(**ps_selection)

        # Select first spw (min id) if not user-selected
        if not selection or 'spw_name' not in selection:
            spw_ps = selected_ps if selected_ps is not None else ps
            first_spw_name = self._get_first_spw_name(spw_ps)
            spw_selection = {'spw_name': first_spw_name}
            selected_ps = selected_ps.sel(**spw_selection) if selected_ps else ps.sel(**spw_selection)
            selection = selection | spw_selection if selection else spw_selection

        return selected_ps, selection


    def _get_first_spw_name(self, ps):
        ''' Return spw selection by name (str or list) or first by frequency if selection is None '''
        # Collect spw names by id
        spw_names = {}
        for key in ps:
            freq_xds = ps[key].frequency
            spw_names[freq_xds.spectral_window_id] = freq_xds.spectral_window_name

        # spw not selected: select first spw by id
        first_spw_id = min(spw_names)
        first_spw_name = spw_names[first_spw_id]
        spw_df = ps.summary()[ps.summary()['spw_name'] == first_spw_name]
        self._logger.info(f"Selecting first spw id {first_spw_id}: {first_spw_name} with range {spw_df.at[spw_df.index[0], 'start_frequency']:e} - {spw_df.at[spw_df.index[0], 'end_frequency']:e}")
        return first_spw_name


    def _calc_amp_color_limits(self, ps, vis_axis):
        # Calculate colorbar limits from amplitude stats for unflagged data
        self._logger.info("Calculating stats for colorbar limits.")
        start = time.time()
        min_val, max_val, mean, std = self._get_ms_stats(ps, vis_axis)
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


    def _get_ms_stats(self, ps, vis_axis):
        # Calculate stats (min, max, mean, std) for visibility axis in processing set
        return calculate_ms_stats(ps, self._ms_path, vis_axis, self._logger)
