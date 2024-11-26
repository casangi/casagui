'''
Implementation of the ``MsRaster`` application for measurement set raster plotting and editing
visibilities
'''

import os
import time

from ..data.measurement_set._ms_data import is_vis_axis, get_correlated_data
from ..data.measurement_set._ms_select import select_ps 
from ..data.measurement_set._ms_stats import calculate_ms_stats 
from ..data.measurement_set._raster_data import raster_data
from ..plot import raster_plot
from ..plots._ms_plot import MsPlot

class MsRaster(MsPlot):
    '''
    Plot MeasurementSet data as raster plot.

    Args:
        ms (str): path in MSv2 (.ms) or MSv4 (.zarr) format.
        log_level (str): logging threshold, default 'INFO'

    Example:
        from casagui.plots import MsRaster
        msr = MsRaster(vis='myvis.ms')
        msr.summary()
        msr.plot(x_axis='frequency', y_axis='time', vis_axis='amp', data_group='base')
        msr.show()
        msr.save() # saves as {ms name}_raster.png
    '''

    def __init__(self, ms, log_level="INFO"):
        super().__init__(ms, log_level, logger_name="MsRaster")
        self._spw_color_limits = {}

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

        # Apply selection to processing set (select spw before calculating colorbar limits)
        selected_ps, selection = self._select_spw(selection)
        self._logger.info(f"Plotting {len(selected_ps)} msv4 datasets.")
        self._logger.debug(f"Processing set maximum dimensions: {selected_ps.get_ps_max_dims()}")

        # Colorbar limits
        if vis_axis == 'amp':
            # For amplitude, limit colorbar range using ms stats
            spw_name = selection['spw_name']
            if spw_name in self._spw_color_limits:
                color_limits = self._spw_color_limits[spw_name]
            else:
                color_limits = self._calc_amp_color_limits(selected_ps, data_group)
                self._spw_color_limits[spw_name] = color_limits
        else:
            color_limits = None
        if color_limits:
            self._logger.info(f"Setting colorbar limits: ({color_limits[0]:.4f}, {color_limits[1]:.4f}).")
        else:
            self._logger.info("Autoscale colorbar limits")

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

    def show(self, hist=False):
        ''' 
        Show interactive Bokeh plot in a browser. Plot tools include pan, zoom, hover, and save.
            hist (bool): Whether to compute and adjoin histogram to plot.
        '''
        title="MsRaster " + self._ms_basename
        super().show(title, hist)

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
        if not filename:
            filename = f"{self._ms_basename}_raster.png"
        super().save(filename, fmt, hist, backend, resources, toolbar, title)

    def _check_plot_inputs(self, x_axis, y_axis, vis_axis, data_group, selection):
        ''' Check plot parameters against processing set xds variables '''
        if data_group not in self.get_data_groups():
            raise ValueError(f"Invalid data_group {data_group}. Use get_data_groups() to see options.")

        # Reassign x_axis or y_axis for spectrum data dimension
        correlated_data = get_correlated_data(self._ps.get(0), data_group)
        x_axis = "antenna_name" if x_axis == "baseline" and correlated_data == "SPECTRUM" else x_axis
        y_axis = "antenna_name" if y_axis == "baseline" and correlated_data == "SPECTRUM" else y_axis

        data_dims = list(self._ps.get(0)[correlated_data].dims)
        if x_axis not in data_dims or y_axis not in data_dims:
            raise ValueError(f"Invalid x or y axis, please select from {data_dims}")

        if not is_vis_axis(vis_axis):
            raise ValueError(f"Invalid vis_axis {vis_axis}")

        if selection and not isinstance(selection, dict):
            raise RuntimeError("selection must be dictionary")

        return x_axis, y_axis

    def _select_spw(self, selection):
        ''' Select first spw (minimum spectral_window_id) if not user-selected '''
        if not selection or 'spw_name' not in selection:
            first_spw_name = self._get_first_spw_name(self._ps)
            spw_selection = {'spw_name': first_spw_name}
        else:
            spw_selection = {'spw_name': selection['spw_name']}

        self._logger.info(f"Applying spw selection to processing set: {spw_selection}")
        selected_ps = self._ps.sel(**spw_selection)
        selection = selection | spw_selection if selection else spw_selection
        return selected_ps, selection

    def _get_first_spw_name(self, ps):
        ''' Return first spw id name '''
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
