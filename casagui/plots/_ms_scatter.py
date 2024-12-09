'''
Implementation of the ``MsScatter`` application for measurement set scatter plotting and editing
visibility/spectrum data
'''

import os
import time

from graphviper.utils.logger import setup_logger

from ..data.measurement_set._scatter_data import scatter_data
from ..plot import scatter_plot
from ..plots._ms_plot import MsPlot

class MsScatter(MsPlot):
    '''
    Plot MeasurementSet data as scatter plot.

    Args:
        ms (str): path in MSv2 (.ms) or MSv4 (.zarr) format.
        log_level (str): logging threshold, default 'INFO'
        interactive (bool): whether to launch interactive GUI in browser. Default False.


    Example:
        from casagui.plots import MsScatter
        mss = MsScatter(ms='myms.ms')
        mss.summary()
        mss.plot(xaxis='frequency', yaxis='amp')
        mss.show()
        mss.save() # saves as {ms name}_scatter.png
    '''

    def __init__(self, ms, log_level="INFO", interactive=False):
        super().__init__(ms, log_level, "MsScatter", interactive)
        if interactive:
            self._logger.warn("Interactive GUI not implemented.")
            self._interactive = False

    def plot(self, x_axis='time', y_axis='amp', data_group='base', selection=None):
        '''
        Create a scatter plot with specified xaxis and yaxis.
            x_axis (str): Plot x-axis. Default 'time'.
            y_axis (str): Plot y-axis. Default 'amp'.
            data_group (str): xds data group name of correlated data, flags, weights, and uvw.  Default 'base'.
                Use list_data_groups() to see options.
            selection (dict): selected data to plot. Options include:
                Processing set selection:
                    'name', 'intents', 'shape', 'polarization', 'scan_number', 'spw_name', 'field_name', 'source_name', 'field_coords', 'start_frequency', 'end_frequency': select by summary() column names
                    'query': for pandas query of summary() columns.
                MSv4 selection:
                    Visibility dims: 'baseline' 'time', 'frequency', 'polarization'
                    Spectrum dims: 'antenna_name', 'time', 'frequency', 'polarization'
                    Use list_antennas() for antenna names. Select 'baseline' as "<name1> & <name2>".
                    Use summary() to list frequencies and polarizations.
                    TODO: how to select time?

        If not interactive and plotting is successful, use show() or save() to view/save the plot.
        '''
        start = time.time()
        scatter_ps = scatter_data(self._ps, x_axis, y_axis, selection, data_group, self._logger)
        for xds in scatter_ps.values():
            print("scatter ps xds:", xds)

        if self._interactive:
            pass # send scatter_data to gui
        else:
            ms_name = os.path.basename(self._ms_path)
            self._plot = scatter_plot(scatter_xds, x_axis, y_axis, ms_name, self._logger)
        if self._plot is None:
            raise RuntimeError("Plot failed.")
        self._logger.debug(f"Plot elapsed time: {time.time() - start:.2f}s.")

    def show(self, hist=False):
        ''' 
        Show interactive Bokeh plot in a browser. Plot tools include pan, zoom, hover, and save.
            hist (bool): Whether to compute and adjoin histogram to plot.
        '''
        title="MsScatter " + self._ms_basename
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
            filename = f"{self._ms_basename}_scatter.png"
        super().save(filename, fmt, hist, backend, resources, toolbar, title)
