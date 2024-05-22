'''
Implementation of the ``VisRaster`` application for plotting and editing
visibilities
'''

import hvplot
import holoviews as hv
import os.path
import time

from ..data._ps_utils import apply_ps_selection, concat_ps_xds
from ..data._xds_utils import set_name_dims
from ..data._vis_stats import calculate_vis_stats 
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

    def __init__(self, vis):
        self._ps, self._vis_path = get_processing_set(vis)
        self._vis_basename = os.path.splitext(os.path.basename(self._vis_path))[0]
        n_datasets = len(self._ps.keys())
        if n_datasets == 0:
            raise RuntimeError("Failed to read visibility file into processing set")
        print(f"Processing {n_datasets} msv4 datasets")

        # Set baseline names as dimension, add ant1 and ant2 names
        #start = time.time()
        for key in self._ps:
            self._ps[key] = set_name_dims(self._ps[key])
        #print(f"Setting baseline names took {time.time() - start} s")

        self._plot = None
        self._ddi_color_limits = {}


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


    def plot(self, x_axis='baseline', y_axis='time', vis_axis='amp', selection=None):
        '''
        Create a y_axis vs x_axis raster plot of visibilities.
        Plot axes include ddi, time, baseline, channel, and polarization.  The axes not set as plot axes can be selected, else the first will be used.

        Args:
            x_axis (str): Plot x-axis. Default 'baseline'.
            y_axis (str): Plot y-axis. Default 'time'.
            vis_axis (str): Visibility component. Default 'amp'.
            selection (dict): selected data to plot. Options include:
              Metadata selection:
                field (int or str):  Default '', all fields in ddi.
                intent (str): Default '', all intents in ddi.
              Plot selection:
                ddi, time, baseline, channel, polarization: select dimensions not being plotted. Default is index 0.
        '''
        select_ddi = 'ddi' not in (x_axis, y_axis)
        selected_ps, selection = apply_ps_selection(self._ps, selection, select_ddi)
        #color_limits = self._set_ddi_color_limits(selected_ps, selection, vis_axis)
        color_limits = None
        plot_xds = concat_ps_xds(selected_ps)

        # Describe plot xds
        shape = plot_xds.sizes
        vis_desc = "Plotting visibilities with "
        if 'ddi' in shape:
            vis_desc += f"{shape['ddi']} ddis, "
        else:
            vis_desc += "1 ddi, "
        vis_desc += f"{shape['time']} times, {shape['baseline']} baselines, {shape['frequency']} channels, {shape['polarization']} polarizations"
        print(vis_desc)

        # Plot xds
        self._plot = raster_plot(plot_xds, x_axis, y_axis, vis_axis, selection, self._vis_path, color_limits)
        if self._plot is None:
            raise RuntimeError("Plot failed.")

    def waterfall_plot(self, vis_axis='amp', selection=None, baselines=None):
        selected_ps, selection = apply_ps_selection(self._ps, selection, True)
        plot_xds = concat_ps_xds(selected_ps)
        if not baselines:
            baselines = (0, min(4, plot_xds.sizes['baseline']))

        #color_limits = self._set_ddi_color_limits(selected_ps, selection, vis_axis)
        color_limits = None
        plot_list = []

        for i in range(baselines[0], baselines[1]):
            print("Plotting baseline", i)
            selection['baseline'] = i
            plot = raster_plot(plot_xds, "frequency", 'time', vis_axis, selection, self._vis_path, color_limits)
            if plot:
                plot_list.append(plot)
        self._plot = hv.Layout(plot_list).cols(2)
 
    def show(self):
        ''' 
        Show interactive Bokeh plot in a browser.
        Plot tools include pan, zoom, hover, and save.
        Groupby axes have selectors: slider, dropdown, etc.
        '''
        if self._plot is None:
            raise RuntimeError("No plot to show.  Run plot() to create plot.")
        hvplot.show(self._plot, title="VisRaster " + self._vis_basename)


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

        print(f"Saving plot to {filename}")
        start = time.time()
        if hist:
            hvplot.save(self._plot.hist(), filename=filename, fmt=fmt, backend=backend, resources=resources, toolbar=toolbar, title=title)
        else:
            hvplot.save(self._plot, filename=filename, fmt=fmt, backend=backend, resources=resources, toolbar=toolbar, title=title)
        print(f"Saving plot took {time.time() - start} s")


    def _set_ddi_color_limits(self, selected_ps, selection, vis_axis):
        if 'amp' not in vis_axis or 'ddi' not in selection:
            return None

        ddi = selection['ddi']
        if ddi in self._ddi_color_limits:
            return self._ddi_color_limits[ddi]

        print("Calculating colorbar limits for amplitude...")
        vis_type = 'corrected' if 'corrected' in vis_axis else 'data'
        min_val, max_val, mean, std = calculate_vis_stats(selected_ps, self._vis_path, vis_type)
        data_min = min(0.0, min_val)
        clip_min = max(data_min, mean - (3.0 * std))
        data_max = max(0.0, max_val)
        clip_max = min(data_max, mean + (3.0 * std))
        color_limits = (clip_min, clip_max)
        self._ddi_color_limits[ddi] = color_limits
        print(f"Setting colorbar limits ({clip_min:.4f}, {clip_max:.4f})")
        return color_limits
