'''
Implementation of the ``VisScatter`` application for plotting and editing
visibilities
'''

from ..io import get_processing_set
from ..plot import scatter_plot
import hvplot

class VisScatter:
    '''
    Plot visibility data as scatter plot.

    Args:
        vis (str): visibility path in MSv2 (.ms) or MSv4 (.zarr) format.

    Example:
        vs = VisScatter(vis='myvis.ms')
        vs.plot(xaxis='time', yaxis='amp')
        vs.save() # saves as {vis}_scatter.png
    '''

    def __init__(self, vis):
        self._ps, self._vis_path = get_processing_set(vis)
        n_datasets = len(self._ps.keys())
        if n_datasets == 0:
            raise RuntimeError("Failed to read visibility file into processing set")
        print(f"Processing {n_datasets} msv4 datasets")
        self._plot = None

    def plot(self, xaxis='time', yaxis='amp', interactive=False):
        '''
        Create a scatter plot with specified xaxis and yaxis.
            xaxis (str): Plot x-axis. Default 'time'.
            yaxis (str): Plot y-axis. Default 'amp'.
            interactive (bool): Whether to display plot in browser (no GUI). Default False.

        If interactive, the plot will be displayed in a web browser where the
        user can inspect the Bokeh plot with pan, zoom, locate, etc.
        '''
        self._plot = scatter_plot(self._ps, xaxis, yaxis)
        if self._plot and interactive:
            hvplot.show(self._plot)
       
    def save(self, plotfile=''):
        '''
        Save plot to file.
            plotfile (str): Name of plot file to save.

        If plotfile is set, the plot will be exported to the specified
        filename in the format of its extension.  If not set, the plot
        will be saved as a PNG with name {vis}_scatter.png.
        '''
        if not self._plot:
            raise RuntimeError("No plot to save.  Run plot() to create plot.")

        if not plotfile:
            plotfile = os.path.splitext(os.path.basename(self._vis_name))[0] + "_scatter.png"

        print(f"Saving plot to {plotfile}")
        hvplot.save(self._plot, plotfile)
