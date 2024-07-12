'''
Implementation of the ``VisRaster`` application for plotting and editing
visibilities
'''

import hvplot
import holoviews as hv
import os.path
import time

from graphviper.utils.logger import setup_logger

from ..data._ps_utils import apply_ps_selection, concat_ps_xds
from ..data._vis_data import is_vis_axis, get_vis_data_var
from ..data._vis_stats import calculate_vis_stats 
from ..data._xds_utils import set_coordinates
from ..io import get_processing_set
from ..plot import raster_plot

class VisRaster:
    '''
    Plot visibilities as raster plot.

    Args:
        vis (str): visibility path in MSv2 (.ms) or MSv4 (.zarr) format.

    Example:
        vr = VisRaster(vis='myvis.ms')
        vr.summary()
        vr.plot(x_axis='baseline_id', y_axis='time', vis_axis='amp') # same as vr.plot()
        vr.show()
        vr.save('myplot.png')
    '''

    def __init__(self, vis, log_level="INFO"):
        # Processing set
        self._ps, self._vis_path = get_processing_set(vis)
        n_datasets = len(self._ps.keys())
        if n_datasets == 0:
            raise RuntimeError("Failed to read visibility file into processing set")

        # Logger
        self._logger = setup_logger(logger_name="VisRaster", log_to_term=True, log_to_file=False, log_level=log_level)
        self._logger.info(f"Processing set contains {n_datasets} msv4 datasets.")

        # Set baseline names and units for plotting
        for key in self._ps:
            self._ps[key] = set_coordinates(self._ps[key])

        # Vis name (no path) for plot title and save filename
        self._vis_basename = os.path.splitext(os.path.basename(self._vis_path))[0]
        self._plot = None


    def summary(self):
        ''' Print processing set summary '''
        summary = self._ps.summary()
        for row in summary.itertuples(index=False): #, name=None):
            name, ddi, intent, field_id, field_name, start_freq, end_freq, shape, field_coords = row
            print("-----")
            print(f"ddi {ddi}: {shape[0]} times, {shape[1]} baselines, {shape[2]} channels, {shape[3]} polarizations")
            print(f"intent: {intent}")
            print(f"field: {field_name} ({field_id})")
            print(f"field coordinates: {field_coords[1]} {field_coords[2]} ({field_coords[0]})")
            print(f"frequency range: {start_freq:e} - {end_freq:e}")
        print("-----")


    def plot(self, x_axis='baseline', y_axis='time', vis_axis='amp', selection=None):
        '''
        Create a static y_axis vs x_axis raster plot of visibilities after applying selection.
        Plot axes include ddi, time, baseline, channel, and polarization.  The axes not set as plot axes can be selected, else the first will be used.

        Args:
            x_axis (str): Plot x-axis. Default 'baseline'.
            y_axis (str): Plot y-axis. Default 'time'.
            vis_axis (str): Visibility component and type (corrected, model). Default 'amp'.
            selection (dict): selected data to plot. Options include:
              Metadata selection:
                field (int or str):  Default '', all fields in ddi.
                intent (str): Default '', all intents in ddi.
              Plot selection:
                ddi, time, baseline, channel, polarization: select dimensions not being plotted. Default is index 0.

        If plotting is successful, use show() or save() to view/save the plot.
        '''
        start_plot = time.time()
        self._check_plot_inputs(x_axis, y_axis, vis_axis, selection)

        # Select ddi if needed
        selection = self._select_ddi(x_axis, y_axis, selection)

        # Apply metadata (ddi, field, intent) selection to processing set.
        selected_ps = apply_ps_selection(self._ps, selection, self._logger)
        self._logger.info(f"Plotting {len(selected_ps)} msv4 datasets.")
        self._logger.debug(f"Processing set maximum dimensions: {selected_ps.get_ps_max_dims()}")

        # For amplitude, limit colorbar range using visibility stats
        # TODO: save and reuse color limits?
        color_limits = self._amp_color_limits(selected_ps, vis_axis)

        # Plot selected processing set
        self._plot = raster_plot(selected_ps, x_axis, y_axis, vis_axis, selection, self._vis_path, color_limits, self._logger)
        if self._plot is None:
            raise RuntimeError("Plot failed.")
        plot_time = time.time() - start_plot
        self._logger.debug(f"Plot elapsed time: {plot_time:.2f}s.")

    def show(self):
        ''' 
        Show interactive Bokeh plot in a browser.
        Plot tools include pan, zoom, hover, and save.
        Groupby axes have selectors: slider, dropdown, etc.
        '''
        if self._plot is None:
            raise RuntimeError("No plot to show.  Run plot() to create plot.")
        hvplot.show(self._plot, title="VisRaster " + self._vis_basename, threaded=True)


    def save(self, filename='', fmt='auto', hist=False, backend='bokeh', resources='online', toolbar=None, title=None):
        '''
        Save plot to file.
            filename (str): Name of file to save. Default '': see below.
            fmt (str): Format of file to save ('png', 'svg', 'html', or 'gif'. Default 'auto': inferred from filename.
            hist (bool): Whether to compute and adjoin histogram.  Default False.
            backend (str): rendering backend, 'bokeh' or 'matplotlib'.  Default None = 'bokeh'.
            resources (str): whether to save with 'online' or 'offline' resources.  'offline' creates a larger file. Default 'online'.
            toolbar (bool): Whether to include the toolbar in the exported plot (True) or not (False). Default None = display the toolbar unless plotfile is png.
            title (str): Custom title for exported HTML file.

        If plotfile is set, the plot will be exported to the specified filename in the format of its extension (see fmt options).  If not set, the plot will be saved as a PNG with name {vis}_raster.png.

        '''
        if self._plot is None:
            raise RuntimeError("No plot to save.  Run plot() to create plot.")

        if not filename:
            filename = f"{self._vis_basename}_raster.png"
        resources = 'inline' if resources == 'offline' else 'cdn'

        start = time.time()
        if hist:
            hvplot.save(self._plot.hist(), filename=filename, fmt=fmt, backend=backend, resources=resources, toolbar=toolbar, title=title)
        else:
            hvplot.save(self._plot, filename=filename, fmt=fmt, backend=backend, resources=resources, toolbar=toolbar, title=title)
        self._logger.info(f"Saved plot to {filename}.")
        self._logger.debug(f"Save elapsed time: {time.time() - start:.3f} s.")


    def _check_plot_inputs(self, x_axis, y_axis, vis_axis, selection):
        if not is_vis_axis(vis_axis):
            raise ValueError(f"Invalid vis_axis {vis_axis}")

        # TODO: are vis types in all xds in ps? Checking first one
        first_xds = self._ps.get(0)

        vis_data = get_vis_data_var(vis_axis)
        if vis_data not in first_xds.data_vars:
            raise ValueError(f"vis_axis {vis_axis} does not exist in dataset")

        valid_axes = list(first_xds[vis_data].dims)
        valid_axes.append('ddi')
        if x_axis not in valid_axes or y_axis not in valid_axes:
            raise ValueError(f"Invalid x or y axis, please select from {valid_axes}")

        if selection and not isinstance(selection, dict):
            raise RuntimeError("selection must be dictionary")


    def _select_ddi(self, x_axis, y_axis, selection):
        ''' Add ddi selection if not plot axis and not selected '''
        # ddi selection exists or is not needed when a plot axis
        if (selection and 'ddi' in selection.keys()) or 'ddi' in (x_axis, y_axis):
            return selection

        # Select first ddi
        selection = {} if selection is None else selection
        selection['ddi'] = min(self._ps.summary()['ddi'].tolist())
        return selection


    def _amp_color_limits(self, ps, vis_axis):
        # Calculate colorbar limits from amplitude stats
        if 'amp' not in vis_axis:
            return None

        self._logger.info("Calculating stats for colorbar limits.")
        start = time.time()
        min_val, max_val, mean, std = self._get_vis_stats(ps, vis_axis)
        data_min = min(0.0, min_val)
        clip_min = max(data_min, mean - (3.0 * std))
        data_max = max(0.0, max_val)
        clip_max = min(data_max, mean + (3.0 * std))
        color_limits = (clip_min, clip_max)
        self._logger.debug(f"Stats elapsed time: {time.time() - start:.2f} s.")
        self._logger.info(f"Setting colorbar limits: ({clip_min:.4f}, {clip_max:.4f}).")
        return color_limits


    def _get_vis_stats(self, ps, vis_axis):
        # Calculate stats (min, max, mean, std) for visibility axis in processing set
        return calculate_vis_stats(ps, self._vis_path, vis_axis, self._logger)
