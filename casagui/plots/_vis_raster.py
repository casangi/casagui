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

    def plot(self, ddi=None, x_axis='baseline_id', y_axis='time', vis_axis='amp', interactive=False):
        '''
        Create a raster plot of visibilities with specified xaxis and yaxis.
            ddi (int): ddi to plot. Default is first ddi numerically.
            xaxis (str): Plot x-axis. Default 'baseline_id'.
            yaxis (str): Plot y-axis. Default 'time'.
            vis_axis (str): Visibility component. Default 'amp'.
            interactive (bool): Whether to display plot in browser (no GUI). Default False.

        If interactive, the plot will be displayed in a web browser where the
        user can inspect the Bokeh plot with pan, zoom, locate, etc.
        '''
        self._plot = raster_plot(self._ps, ddi, x_axis, y_axis, vis_axis, self._vis_path)
        if self._plot and interactive:
            hvplot.show(self._plot)
       
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
