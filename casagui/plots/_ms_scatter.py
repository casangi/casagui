'''
Implementation of the ``MSScatter`` application for plotting and editing
visibility/spectrum data
'''

import os
import time

from graphviper.utils.logger import setup_logger

from ..data.measurement_set._ps_utils import summary
from ..data.measurement_set._scatter_data import scatter_data
from ..io import get_processing_set
from ..plot import scatter_plot
from ..plots._ms_plot import show, save

class MSScatter:
    '''
    Plot MeasurementSet data as scatter plot.

    Args:
        ms (str): path in MSv2 (.ms) or MSv4 (.zarr) format.
        log_level (str): logging threshold, default 'INFO'

    Example:
        mss = MSScatter(ms='myms.ms')
        mss.summary()
        mss.plot(xaxis='time', yaxis='amp') # default, same as mss.plot() with no arguments
        mss.show()
        mss.save() # saves as {ms name}_scatter.png
    '''

    def __init__(self, ms, log_level="INFO"):
        # Logger
        self._logger = setup_logger(logger_name="MSScatter", log_to_term=True, log_to_file=False, log_level=log_level)

        self._ps, self._ms_path = get_processing_set(ms)
        # MS name (no path) for plot title and save filename
        self._ms_basename = os.path.splitext(os.path.basename(self._ms_path))[0]

        n_datasets = len(self._ps)
        if n_datasets == 0:
            raise RuntimeError("Failed to read visibility file into processing set")
        self._logger.info(f"Processing set contains {n_datasets} msv4 datasets.")

        self._plot = None


    def summary(self, columns=None):
        ''' Print processing set summary.
            Args: columns (None, str, list): type of metadata to list.
                None:      Print all summary columns in processing set.
                'by_msv4': Print formatted summary metadata per MSv4.
                str, list: Print a subset of summary columns in processing set.
                           Options include 'name', 'intents', 'shape', 'polarization', 'scan_number', 'spw_name', 'field_name', 'source_name', 'field_coords', 'start_frequency', 'end_frequency'
        '''
        summary(self._ps, columns)


    def plot(self, x_axis='time', y_axis='amp', selection=None, showgui=False):
        '''
        Create a scatter plot with specified xaxis and yaxis.
            x_axis (str): Plot x-axis. Default 'time'.
            y_axis (str): Plot y-axis. Default 'amp'.
            selection (dict): Selected data to plot.  Options include:
                Summary column names: 'name', 'intents', 'shape', 'polarization', 'spw_name', 'field_name', 'source_name', 'field_coords', 'start_frequency', 'end_frequency'
                'query': for pandas query of summary columns.
            showgui (bool): Whether to launch interactive GUI in browser. Default False.

        TODO: add selection
        '''
        start = time.time()
        scatter_xds = scatter_data(self._ps, x_axis, y_axis, selection, self._logger)

        if showgui:
            raise RuntimeError("Interactive GUI not implemented.")
        elif self._plot is None:
            self._plot = scatter_plot(self._ps, xaxis, yaxis)
            raise RuntimeError("Plot failed.")
        self._logger.debug(f"Plot elapsed time: {time.time() - start:.2f}s.")

    def show(self):
        ''' 
        Show interactive Bokeh plot in a browser.
        Plot tools include pan, zoom, hover, and save.
        '''
        title="MSScatter " + self._ms_basename
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
        start = time.time()
        if not filename:
            filename = f"{self._vis_basename}_scatter.png"

        save(self._plot, filename, fmt, hist, backend, resources, toolbar, title)
        self._logger.info(f"Saved plot to {filename}.")
        self._logger.debug(f"Save elapsed time: {time.time() - start:.3f} s.")
