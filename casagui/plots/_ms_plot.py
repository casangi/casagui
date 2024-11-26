'''
Common functions for ms plots (raster and scatter)
'''
import os
import time

import hvplot
import pandas as pd

from xradio.measurement_set.processing_set import ProcessingSet
from graphviper.utils.logger import setup_logger

from ..data.measurement_set._ms_utils import set_baseline_coordinate
from ..io._ms_io import get_processing_set

class MsPlot:
    def __init__(self, ms, log_level="INFO", logger_name="MsPlot"):
        # Logger
        self._logger = setup_logger(logger_name, log_to_term=True, log_to_file=False, log_level=log_level)

        # COnvert ms to zarr, get ProcessingSet
        self._ps, self._ms_path = get_processing_set(ms, self._logger)

        # ms basename (no path) for plot title and save filename
        self._ms_basename = os.path.splitext(os.path.basename(self._ms_path))[0]

        # Set baseline names instead of ids
        set_baseline_coordinate(self._ps)

        # For show() and save()
        self._plot = None

    def summary(self, columns=None):
        ''' Print ProcessingSet summary.
            Args:
                ps (xradio ProcessingSet): ps for summary
                columns (None, str, list): type of metadata to list.
                    None:      Print all summary columns in ProcessingSet.
                    'by_msv4': Print formatted summary metadata by MSv4.
                    str, list: Print a subset of summary columns in ProcessingSet.
                        Options include 'name', 'intents', 'shape', 'polarization', 'scan_number', 'spw_name', 'field_name', 'source_name', 'field_coords', 'start_frequency', 'end_frequency'
        '''
        pd.set_option("display.max_rows", len(self._ps))
        pd.set_option("display.max_columns", 12)
        ps_summary = self._ps.summary()

        if columns is None:
            print(ps_summary)
        elif columns == "by_msv4":
            for row in ps_summary.itertuples(index=False):
                name, intents, shape, polarization, scan_number, spw_name, field_name, source_name, line_name, field_coords, start_frequency, end_frequency = row
                print("-----")
                print(f"MSv4 name: {name}")
                print(f"intent: {intents}")
                print(f"shape: {shape[0]} times, {shape[1]} baselines, {shape[2]} channels, {shape[3]} polarizations")
                print(f"polarization: {polarization}")
                print(f"scan_number: {scan_number}")
                print(f"spw_name: {spw_name}")
                print(f"field_name: {field_name}")
                print(f"source_name: {source_name}")
                print(f"line_name: {line_name}")
                print(f"field_coords: ({field_coords[0]}) {field_coords[1]} {field_coords[2]}")
                print(f"frequency range: {start_frequency:e} - {end_frequency:e}")
            print("-----")
        else:
            if isinstance(columns, str):
                columns = [columns]
            summary_columns = []
            for column in columns:
                if column in ps_summary.columns:
                    summary_columns.append(column)
                else:
                    print(f"Ignoring invalid summary column: {column}")
            print(ps_summary[summary_columns])

    def get_data_groups(self):
        ''' Get data groups from all ProcessingSet ms_xds. Returns set. '''
        data_groups = []
        for xds_name in self._ps:
            data_groups.extend(list(self._ps[xds_name].attrs['data_groups']))
        return set(data_groups)

    def get_antennas(self, plot_positions=False):
        ''' Print antenna names in ProcessingSet antenna_xds, optionally plot antenna positions '''
        if plot_positions:
            self._ps.plot_antenna_positions()
        return self._ps.get_combined_antenna_xds().antenna_name.values.tolist()

    def plot_phase_centers(self, label_all_fields=False, data_group='base'):
        ''' Plot the phase center locations of all fields in the Processing Set and label central field.
                label_all_fields (bool); label all fields on the plot
                data_group (str); data group to use for processing.
        '''
        self._ps.plot_phase_centers(label_all_fields, data_group)

    def show(self, title='MsPlot', hist=False):
        ''' 
        Show interactive Bokeh plot in a browser.  Plot tools include pan, zoom, hover, and save.
            title (str): Browser tab title.
            hist (bool): Whether to compute and adjoin histogram to plot.
        '''
        if self._plot is None:
            raise RuntimeError("No plot to show.  Run plot() to create plot.")

        if hist:
            hvplot.show(self._plot.hist(), title=title)
        else:
            hvplot.show(self._plot, title=title)


    def save(self, filename='ms_plot.png', fmt='auto', hist=False, backend='bokeh', resources='online', toolbar=None, title=None):
        '''
        Save plot to file.
            filename (str): Name of file to save.
            fmt (str): Format of file to save ('png', 'svg', 'html', or 'gif') or 'auto': inferred from filename.
            hist (bool): Whether to compute and adjoin histogram to plot.
            backend (str): rendering backend, 'bokeh' or 'matplotlib'.
            resources (str): whether to save with 'online' or 'offline' resources.  'offline' creates a larger file.
            toolbar (bool): Whether to include the toolbar in the exported plot.
            title (str): Custom title for exported HTML file.
        '''
        if self._plot is None:
            raise RuntimeError("No plot to save.  Run plot() to create plot.")

        start = time.time()
        # embed BokehJS resources inline for offline use, else use content delivery network
        resources = 'inline' if resources == 'offline' else 'cdn'

        if hist:
            hvplot.save(self._plot.hist(), filename=filename, fmt=fmt, backend=backend, resources=resources, toolbar=toolbar, title=title)
        else:
            hvplot.save(self._plot, filename=filename, fmt=fmt, backend=backend, resources=resources, toolbar=toolbar, title=title)
        self._logger.info(f"Saved plot to {filename}.")
        self._logger.debug(f"Save elapsed time: {time.time() - start:.3f} s.")
