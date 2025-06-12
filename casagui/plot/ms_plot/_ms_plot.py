'''
Base class for ms plots
'''

import os
import time

from bokeh.plotting import show
import hvplot
import holoviews as hv
import numpy as np
import panel as pn

try:
    from toolviper.utils.logger import setup_logger
    _HAVE_TOOLVIPER = True
except ImportError:
    _HAVE_TOOLVIPER = False

from casagui.data.measurement_set._ms_data import MsData
from casagui.toolbox import AppContext
from casagui.utils._logging import get_logger

class MsPlot:

    ''' Base class for MS plots with common functionality '''

    def __init__(self, ms=None, log_level="info", show_gui=False, app_name="MsPlot"):
        if not ms and not show_gui:
            raise RuntimeError("Must provide ms/zarr path if gui not shown.")

        # Set logger: use toolviper logger else casalog else python logger
        if _HAVE_TOOLVIPER:
            self._logger = setup_logger(app_name, log_to_term=True, log_to_file=False, log_level=log_level.upper())
        else:
            self._logger = get_logger()
            self._logger.setLevel(log_level.upper())

        # Save parameters; ms set below
        self._show_gui = show_gui
        self._app_name = app_name

        # Set up temp dir for output html files; do not add casagui bokeh libraries
        self._app_context = AppContext(app_name, init_bokeh=False)

        if show_gui:
            # Enable "toast" notifications
            pn.config.notifications = True
            self._toast = None # for destroy() with new plot or new notification

        # Initialize plot inputs and params
        self._plot_inputs = {}

        # Initialize plots
        self._plot_init = False
        self._plots_locked = False
        self._plots = []

        # Set data (if ms)
        self._data = None
        self._ms_info = {}
        self._set_ms(ms)

    def summary(self, data_group='base', columns=None):
        ''' Print ProcessingSet summary.
            Args:
                data_group (str): data group to use for summary.
                columns (None, str, list): type of metadata to list.
                    None:      Print all summary columns in ProcessingSet.
                    'by_msv4': Print formatted summary metadata by MSv4.
                    str, list: Print a subset of summary columns in ProcessingSet.
                        Options: 'name', 'intents', 'shape', 'polarization', 'scan_name', 'spw_name',
                                 'field_name', 'source_name', 'field_coords', 'start_frequency', 'end_frequency'
            Returns: list of unique values when single column is requested, else None
        '''
        self._data.summary(data_group, columns)

    def data_groups(self):
        ''' Returns set of data groups from all ProcessingSet ms_xds. '''
        return self._data.data_groups()

    def antennas(self, plot_positions=False, label_antennas=False):
        ''' Returns list of antenna names in ProcessingSet antenna_xds.
                plot_positions (bool): show plot of antenna positions.
                label_antennas (bool): label positions with antenna names.
        '''
        return self._data.get_antennas(plot_positions, label_antennas)

    def plot_phase_centers(self, data_group='base', label_fields=False):
        ''' Plot the phase center locations of all fields in the Processing Set and highlight central field.
                data_group (str): data group to use for field and source xds.
                label_fields (bool): label all fields on the plot if True, else label central field only
        '''
        self._data.plot_phase_centers(data_group, label_fields)

    def clear_plots(self):
        ''' Clear plot list '''
        while self._plots_locked:
            time.sleep(1)
        self._plots.clear()

    def clear_selection(self):
        ''' Clear selection in data and restore to original '''
        if self._data:
            self._data.clear_selection()

    def show(self):
        ''' 
        Show interactive Bokeh plots in a browser. Plot tools include pan, zoom, hover, and save.
        '''
        if not self._plots:
            raise RuntimeError("No plots to show.  Run plot() to create plot.")

        # Do not delete plot list until rendered
        self._plots_locked = True

        # Single plot or combine plots into layout using subplots (rows, columns)
        # Not layout if subplots is single plot (default if None) or if only one plot saved
        subplots = self._plot_inputs['subplots']
        layout_plot, is_layout = self._layout_plots(subplots)

        # Render to bokeh figure
        if is_layout:
            # Show plots in columns
            plot = hv.render(layout_plot.cols(subplots[1]))
        else:
            # Show single plot
            plot = hv.render(layout_plot)

        self._plots_locked = False
        show(plot)

# pylint: disable=too-many-arguments, too-many-positional-arguments, too-many-locals
    def save(self, filename='ms_plot.png', fmt='auto', width=900, height=600):
        '''
        Save plot to file with filename, format, and size.
        If iteration plots were created:
            If subplots is a grid, the layout plot will be saved to a single file.
            If subplots is a single plot, iteration plots will be saved individually,
                with a plot index appended to the filename: {filename}_{index}.{ext}.
        '''
        if not self._plots:
            raise RuntimeError("No plot to save.  Run plot() to create plot.")

        start_time = time.time()

        # Save single plot or combine plots into layout using subplots (rows, columns).
        # Not layout if subplots is single plot or if only one plot saved.
        subplots = self._plot_inputs['subplots']
        layout_plot, is_layout = self._layout_plots(subplots)

        if is_layout:
            # Save plots combined into one layout
            hvplot.save(layout_plot.cols(subplots[1]), filename=filename, fmt=fmt)
            self._logger.info("Saved plot to %s.", filename)
        else:
            # Save plots individually, with index appended if exprange='all' and multiple plots.
            if self._plot_inputs['iter_axis'] is None:
                hvplot.save(layout_plot.opts(width=width, height=height), filename=filename, fmt=fmt)
                self._logger.info("Saved plot to %s.", filename)
            else:
                name, ext = os.path.splitext(filename)
                iter_range = self._plot_inputs['iter_range'] # None or (start, end)
                plot_idx = 0 if iter_range is None else iter_range[0]

                for plot in self._plots:
                    exportname = f"{name}_{plot_idx}.{ext}"
                    hvplot.save(plot.opts(width=width, height=height), filename=exportname, fmt=fmt)
                    self._logger.info("Saved plot to %s.", exportname)
                    plot_idx += 1

        self._logger.debug("Save elapsed time: %.2fs.", time.time() - start_time)
# pylint: disable=too-many-arguments, too-many-positional-arguments, too-many-locals

    def _layout_plots(self, subplots):
        subplots = (1, 1) if subplots is None else subplots
        num_plots = len(self._plots)
        num_layout_plots = min(num_plots, np.prod(subplots))

        if num_layout_plots == 1:
            return self._plots[0], False

        # Set plots in layout
        plot_count = 0
        layout = None
        for i in range(num_layout_plots):
            plot = self._plots[i]
            layout = plot if layout is None else layout + plot
            plot_count += 1

        is_layout = plot_count > 1
        return layout, is_layout

    def _set_ms(self, ms):
        ''' Update ms info for input ms filepath (MSv2 or zarr), or None in show_gui mode.
            Return whether ms changed (false if ms is None). '''
        self._ms_info['ms'] = ms
        ms_error = ""
        ms_changed = ms and (not self._data or not self._data.is_ms_path(ms))

        if ms_changed:
            try:
                # Set new MS data
                self._data = MsData(ms, self._logger)
                ms_path = self._data.get_path()
                self._ms_info['ms'] = ms_path
                root, ext = os.path.splitext(os.path.basename(ms_path))
                while ext != '':
                    root, ext = os.path.splitext(root)
                self._ms_info['basename'] = root
                self._ms_info['data_dims'] = self._data.get_data_dimensions()
            except RuntimeError as e:
                ms_error = str(e)
                self._data = None

        if ms_error:
            self._notify(ms_error, 'error', 0)

        return ms_changed

    def _notify(self, message, level, duration=3000):
        ''' Log message. If show_gui, notify user with toast for duration in ms.
            Zero duration must be dismissed. '''
        if self._show_gui:
            pn.state.notifications.position = 'top-center'
            if self._toast:
                self._toast.destroy()

        if level == "info":
            self._logger.info(message)
            if self._show_gui:
                self._toast = pn.state.notifications.info(message, duration=duration)
        elif level == "error":
            self._logger.error(message)
            if self._show_gui:
                self._toast = pn.state.notifications.error(message, duration=duration)
        elif level == "success":
            self._logger.info(message)
            if self._show_gui:
                self._toast = pn.state.notifications.success(message, duration=duration)
        elif level == "warning":
            self._logger.warning(message)
            if self._show_gui:
                self._toast = pn.state.notifications.warning(message, duration=duration)
