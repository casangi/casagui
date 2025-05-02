'''
Base class for ms plots
'''

import os
import time

import hvplot
import numpy as np
import panel as pn

try:
    from toolviper.utils.logger import setup_logger
    _HAVE_TOOLVIPER = True
except ImportError:
    _HAVE_TOOLVIPER = False

from casagui.data.measurement_set._ms_data import MsData
from casagui.plot._ms_plot_constants import PLOT_WIDTH, PLOT_HEIGHT
from casagui.utils._logging import get_logger

class MsPlot:

    ''' Base class for MS plots with common functionality '''

    def __init__(self, ms=None, log_level="info", interactive=False, app_name="MsPlot"):
        if not ms and not interactive:
            raise RuntimeError("Must provide ms/zarr path if not interactive.")

        # Set logger: use toolviper logger else casalog else python logger
        if _HAVE_TOOLVIPER:
            self._logger = setup_logger(app_name, log_to_term=True, log_to_file=False, log_level=log_level.upper())
        else:
            self._logger = get_logger()
            self._logger.setLevel(log_level.upper())

        # Save parameters; ms set below
        self._interactive = interactive
        self._app_name = app_name

        if interactive:
            # enable "toast" notifications
            pn.config.notifications = True
            pn.config.sizing_mode = 'stretch_width'
            pn.state.notifications.position = 'top-center'
            self._toast = None # destroy toast when user does not close

        # Initialize plot inputs and params
        self._plot_inputs = {}
        self._plot_inputs['have_inputs'] = False

        # Initialize plots
        self._plots = []
        self._plot_init = False

        # Set data (if ms)
        self._data = None
        self._ms_info = {}
        self._set_ms(ms)

    def summary(self, columns=None):
        ''' Print ProcessingSet summary.
            Args:
                columns (None, str, list): type of metadata to list.
                    None:      Print all summary columns in ProcessingSet.
                    'by_msv4': Print formatted summary metadata by MSv4.
                    str, list: Print a subset of summary columns in ProcessingSet.
                        Options: 'name', 'intents', 'shape', 'polarization', 'scan_number', 'spw_name',
                                 'field_name', 'source_name', 'field_coords', 'start_frequency', 'end_frequency'
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

    def clear_plots(self):
        ''' Clear plot list '''
        self._plots.clear()

    def clear_selection(self):
        ''' Clear selection in data and restore to original '''
        if self._data:
            self._data.clear_selection()

    def show(self, title=None, port=0):
        ''' 
        Show interactive Bokeh plots in a browser. Plot tools include pan, zoom, hover, and save.
        Multiple plots can be shown in a grid using plot parameter `subplots`.  Default is to show a single plot.
            title (str): browser tab title.  Default is "{app} {ms_name}".
            port (int): optional port number to use.  Default 0 will select a port number.
        '''
        if not self._plots:
            raise RuntimeError("No plots to show.  Run plot() to create plot.")

        if not title:
            title = ' '.join([self._app_name, self._ms_info['basename']]) if not self._interactive else self._app_name

        # Single plot or combine plots into layout using subplots (rows, columns)
        # Not layout if subplots is single plot (default if None) or if only one plot saved
        subplots = self._plot_inputs['subplots']
        subplots = (1, 1) if subplots is None else subplots
        layout_plot, is_layout = self._layout_plots(subplots)

        if is_layout:
            # Show plots in columns
            hvplot.show(layout_plot.cols(subplots[1]), title=title, port=port, threaded=True)
        else:
            # Show single plot
            hvplot.show(layout_plot.opts(width=PLOT_WIDTH, height=PLOT_HEIGHT), title=title, port=port, threaded=True)

    def save(self, filename='ms_plot.png', fmt='auto', export_range='one'):
        '''
        Save plot to file with filename and format. If iteration plots, export 'one' or 'all'.
        '''
        if not self._plots:
            raise RuntimeError("No plot to save.  Run plot() to create plot.")

        start_time = time.time()

        # Single plot or combine plots into layout using subplots (rows, columns).
        # Not layout if subplots is single plot (default if None) or if only one plot saved.
        subplots = self._plot_inputs['subplots']
        subplots = (1, 1) if subplots is None else subplots
        layout_plot, is_layout = self._layout_plots(subplots)

        if is_layout:
            # Save plots combined into one layout
            hvplot.save(layout_plot.cols(subplots[1]), filename=filename, fmt=fmt)
            self._logger.info("Saved plot to %s.", filename)
        else:
            # Save plots individually, with index appended if exprange='all' and multiple plots.
            if self._plot_inputs['iter_axis'] is None or export_range=='one':
                hvplot.save(layout_plot.opts(width=PLOT_WIDTH, height=PLOT_HEIGHT), filename=filename, fmt=fmt)
            else:
                name, ext = os.path.splitext(filename)
                plot_range = self._plot_inputs['iter_range'] # None or (start, end), default (0, 0)
                plot_idx = 0 if plot_range is None else plot_range[0]

                for plot in self._plots:
                    exportname = f"{name}_{plot_idx}.{ext}"
                    hvplot.save(plot.opts(width=PLOT_WIDTH, height=PLOT_HEIGHT), filename=exportname, fmt=fmt)
                    self._logger.info("Saved plot to %s.", exportname)
                    plot_idx += 1

        self._logger.debug("Save elapsed time: %.2fs.", time.time() - start_time)

    def _layout_plots(self, subplots):
        num_plots = len(self._plots)
        num_layout_plots = min(num_plots, np.prod(subplots))

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
        ''' Update ms info for input ms filepath (MSv2 or zarr), or None in interactive mode.
            Return whether ms changed (false if ms is None). '''
        self._ms_info['ms'] = ms
        ms_error = ""
        ms_changed = ms and (not self._data or not self._data.is_ms_path(ms))

        if ms_changed:
            try:
                # Set new MS data
                self._data = MsData(ms, self._logger)
                self._ms_info['ms'] = self._data.get_path()
                self._ms_info['basename'] = self._data.get_basename()
                self._ms_info['data_dims'] = self._data.get_data_dimensions()
            except RuntimeError as e:
                ms_error = str(e)
                self._data = None
        if ms_error:
            self._notify(ms_error, 'error', 0)
        return ms_changed

    def _notify(self, message, level, duration=3000):
        ''' Log message. If interactive, notify user with toast for duration in ms.
            Zero duration must be dismissed. '''
        if self._toast:
            self._toast.destroy()
        if level == "info":
            self._logger.info(message)
            if self._interactive:
                self._toast = pn.state.notifications.info(message, duration=duration)
        elif level == "error":
            self._logger.error(message)
            if self._interactive:
                self._toast = pn.state.notifications.error(message, duration=duration)
        elif level == "success":
            self._logger.info(message)
            if self._interactive:
                self._toast = pn.state.notifications.success(message, duration=duration)
        elif level == "warning":
            self._logger.warning(message)
            if self._interactive:
                self._toast = pn.state.notifications.warning(message, duration=duration)
