'''
Base class for ms plots (raster and scatter)
'''
import os
import time

from bokeh.io import reset_output as reset_bokeh_output
import hvplot

try:
    from toolviper.utils.logger import setup_logger
    _have_toolviper = True
except ImportError:
    _have_toolviper = False
    from casagui.utils._logging import get_logger
    

from casagui.data.measurement_set._ms_data import MsData
from casagui.utils import is_notebook

class MsPlot:

    def __init__(self, ms=None, log_level="info", interactive=False, app_name="MsPlot"):
        if not ms and not interactive:
            raise RuntimeError("Must provide ms/zarr path if not interactive.")

        self._ms = ms
        self._interactive = interactive
        self._app_name = app_name

        self._is_notebook = is_notebook()
        self._plot_inputs = {}
        self._plots = []

        # Set logger: use toolviper logger else casalog else python logger
        if _have_toolviper:
            self._logger = setup_logger(app_name, log_to_term=True, log_to_file=False, log_level=log_level.upper())
        else:
            self._logger = get_logger()
            self._logger.setLevel(log_level.upper())

        self._data = MsData(ms, self._logger)
        self._basename = self._data.get_basename()
        self._app_title = ' '.join([self._app_name, self._basename])

        if interactive:
            from casagui.utils import resource_manager, reset_resource_manager
            self._app_context = AppContext(self._app_title)

    def summary(self, columns=None):
        ''' Print ProcessingSet summary.
            Args:
                columns (None, str, list): type of metadata to list.
                    None:      Print all summary columns in ProcessingSet.
                    'by_msv4': Print formatted summary metadata by MSv4.
                    str, list: Print a subset of summary columns in ProcessingSet.
                        Options include 'name', 'intents', 'shape', 'polarization', 'scan_number', 'spw_name', 'field_name', 'source_name', 'field_coords', 'start_frequency', 'end_frequency'
            Returns: list of unique values when single column is requested, else None
        '''
        self._data.summary(columns)

    def data_groups(self):
        ''' Returns set of data groups from all ProcessingSet ms_xds. '''
        return self._data.get_data_groups()

    def antennas(self, plot_positions=False):
        ''' Returns list of antenna names in ProcessingSet antenna_xds.
            Optionally show plot of antenna positions. '''
        return self._data.get_antennas(plot_positions)

    def plot_phase_centers(self, label_all_fields=False, data_group='base'):
        ''' Plot the phase center locations of all fields in the Processing Set and label central field.
                label_all_fields (bool); label all fields on the plot
                data_group (str); data group to use for processing.
        '''
        self._data.plot_phase_centers(label_all_fields, data_group)

    def clear_selection(self):
        self._data.clear_selection()

    def clear_plots(self):
        self._plots.clear()

    def show(self, title=None, port=0, layout=None):
        ''' 
        Show interactive Bokeh plots in a browser.  Plot tools include pan, zoom, hover, and save.
        Multiple plots can be displayed in a panel layout. Default will show first plot only.
            title (str): browser tab title.
            port (int): allows specifying port number.
            layout (tuple): (start, rows, columns) settings for multiple plots.
        '''
        if not self._plots:
            raise RuntimeError("No plots to show.  Run plot() to create plot.")

        if not title:
            title = self._app_title

        # Single plot or combine plots into layout
        layout = (0, 1, 1) if layout is None else layout # default is first plot only
        plot, is_layout = self._layout_plots(layout)

        if is_layout:
            # Show plots in columns
            hvplot.show(plot.cols(layout[2]), title=title, port=port, threaded=True)
        else:
            # Show single plot
            hvplot.show(plot, title=title, port=port, threaded=True)

    def save(self, filename='ms_plot.png', fmt='auto', layout=None, export_range='one'):
        '''
        Save plot to file.
            filename (str): Name of file to save.
            fmt (str): Format of file to save ('png', 'svg', 'html', or 'gif') or 'auto': inferred from filename.
            layout (tuple): panel layout settings (start, rows, columns) for multiple plots.
            exprange (str): for single plot, whether to save first plot only ('one') or all plots ('all'). Ignored for grid layout.

        When exporting multiple plots as single plots, the plot index will be appended to the filename {filename}_{index}.{ext}.
        '''
        if not self._plots:
            raise RuntimeError("No plot to save.  Run plot() to create plot.")

        # Get single plot, or combine plots into panel layout
        layout = (0, 1, 1) if layout is None else layout 
        plot, is_layout = self._layout_plots(layout)

        start = time.time()
        if is_layout:
            # Save plots combined into one layout
            hvplot.save(plot.cols(layout[2]), filename=filename, fmt=fmt)
            self._logger.info(f"Saved plot to {filename}.")
        else:
            # Save plots individually, with index appended if exprange='all' and multiple plots.
            num_plots = len(self._plots)
            start = layout[0]
            end = num_plots if export_range == 'all' else start + 1
            name, ext = os.path.splitext(filename)

            for i in range(start, end):
                plot = self._plots[i]
                if export_range == 'all' and num_plots > 1:
                    exportname = f"{name}_{i}{ext}"
                else:
                    exportname = filename
                hvplot.save(plot, filename=exportname, fmt=fmt)
                self._logger.info(f"Saved plot to {exportname}.")

        self._logger.debug(f"Save elapsed time: {time.time() - start:.3f} s.")

    def _layout_plots(self, layout):
        if len(layout) != 3:
            raise RuntimeError("Layout should contain (start, rows, columns)")

        start, rows, columns = layout
        num_plots = len(self._plots)
        if start >= num_plots:
            raise IndexError(f"layout start {start} out of range {num_plots}.")

        num_layout_plots = rows * columns
        if num_plots < num_layout_plots:
            num_layout_plots = num_plots

        # Set plots in layout
        layout_plot_count = 0
        layout = None
        for i in range(start, start + num_layout_plots):
            if i >= num_plots:
                break
            plot = self._plots[i]
            layout = plot if layout is None else layout + plot
            layout_plot_count += 1

        is_layout = layout_plot_count > 1
        return layout, is_layout
