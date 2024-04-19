'''
Implementation of the ``VisRaster`` application for plotting and editing
visibilities
'''

import hvplot
import os.path

from ..data import set_baseline_ids
from ..io import get_processing_set
from ..plot import raster_plot

class VisRaster:
    '''
    Plot visibilities as raster plot.

    Args:
        vis (str): visibility path in MSv2 (.ms) or MSv4 (.zarr) format.

    Example:
        vs = VisRaster(vis='myvis.ms')
        vs.plot(x_axis='baseline_id', y_axis='time', vis_axis='amp')
        vs.save('myplot.png')
    '''

    def __init__(self, vis):
        self._ps, self._vis_path = get_processing_set(vis)
        n_datasets = len(self._ps.keys())
        if n_datasets == 0:
            raise RuntimeError("Failed to read visibility file into processing set")
        print(f"Processing {n_datasets} msv4 datasets")

        # Set unique baseline ids
        for key in self._ps:
            set_baseline_ids(self._ps[key])

        self._plot = None

    def summary(self):
        ''' Print processing set summary '''
        summary = self._ps.summary()
        for row in summary.itertuples(index=False): #, name=None):
            name, ddi, intent, field_id, field_name, start_freq, end_freq, shape = row
            print("-----")
            print(f"ddi {ddi}: {shape[0]} times, {shape[1]} baselines, {shape[2]} channels, {shape[3]} polarizations")
            print(f"intent: {intent}")
            print(f"field: {field_name} ({field_id})")
            print(f"frequency range: {start_freq:.3e} - {end_freq:.3e}")

    def plot(self, x_axis='baseline', y_axis='time', vis_axis='amp', selection=None, interactive=False):
        '''
        Create a y_axis vs x_axis raster plot of visibilities.
        Plot axes include time, baseline, channel, and polarization.  The axes not set as display axes can be selected, else the first will be used.

        Args:
            x_axis (str): Plot x-axis. Default 'baseline'.
            y_axis (str): Plot y-axis. Default 'time'.
            selection (dict): selected data to plot. Options include:
              Metadata selection:
                ddi (int):    Default is first ddi numerically.
                field (int or str):  Default is '', all fields in ddi.
                intent (str): Default is '', all intents in ddi.
              Plot selection:
                time, baseline, channel, polarization: select dimensions not being plotted. Default is index 0.
            vis_axis (str): Visibility component. Default 'amp'.
            interactive (bool): Whether to display plot in browser (no GUI). Default False.

        If interactive, the plot will be displayed in a web browser where the
        user can inspect the Bokeh plot with pan, zoom, locate, etc.
        '''
        self._plot = raster_plot(self._ps, x_axis, y_axis, vis_axis, selection, self._vis_path)

        if self._plot and interactive:
            hvplot.show(plot)
       
    def save(self, plotfile=''):
        '''
        Save plot to file.
            plotfile (str): Name of plot file to save.

        If plotfile is set, the plot will be exported to the specified
        filename in the format of its extension.  If not set, the plot
        will be saved as a PNG with name {vis}_raster.png.
        '''
        if not self._plot:
            raise RuntimeError("No plot to save.  Run plot() to create plot.")

        if not plotfile:
            basename = os.path.splitext(os.path.basename(self._vis_path))[0]
            plotfile = f"{basename}_raster.png"

        print(f"Saving plot to {plotfile}")
        hvplot.save(self._plot, plotfile)
