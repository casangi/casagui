'''
Parent class for ms plots (raster and scatter)
'''
import os
import time

import numpy as np
import pandas as pd
import hvplot

from xradio.measurement_set.processing_set import ProcessingSet
from toolviper.utils.logger import setup_logger

from casagui.io._ms_io import get_processing_set
from casagui.data.measurement_set._ms_coords import set_coordinates
from casagui.data.measurement_set._ms_data import is_vis_axis

class MsPlot:
    def __init__(self, ms, log_level="info", logger_name="MsPlot", interactive=False):
        # Logger
        self._logger = setup_logger(logger_name, log_to_term=True, log_to_file=False, log_level=log_level.upper())

        # Convert ms to zarr, get ProcessingSet
        self._ps, self._ms_path = get_processing_set(ms, self._logger)

        for name, ms_xds in self._ps.items():
            self._ps[name] = set_coordinates(ms_xds)

        # ms basename (no path) for plot title and save filename
        self._ms_basename = os.path.splitext(os.path.basename(self._ms_path))[0]

        self._interactive = interactive
        self._plots = []


    def summary(self, columns=None):
        ''' Print ProcessingSet summary.
            Args:
                ps (xradio ProcessingSet): ps for summary
                columns (None, str, list): type of metadata to list.
                    None:      Print all summary columns in ProcessingSet.
                    'by_msv4': Print formatted summary metadata by MSv4.
                    str, list: Print a subset of summary columns in ProcessingSet.
                        Options include 'name', 'intents', 'shape', 'polarization', 'scan_number', 'spw_name', 'field_name', 'source_name', 'field_coords', 'start_frequency', 'end_frequency'
            Returns: list of unique values when single column is requested, else None
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
            col_df = ps_summary[columns]
            print(col_df)
            if len(columns) == 1:
                return self._get_unique_values(col_df)


    def data_groups(self):
        ''' Get data groups from all ProcessingSet ms_xds. Returns set. '''
        data_groups = []
        for xds_name in self._ps:
            data_groups.extend(list(self._ps[xds_name].data_groups))
        return set(data_groups)

    def antennas(self, plot_positions=False):
        ''' Get antenna names in ProcessingSet antenna_xds, optionally plot antenna positions '''
        if plot_positions:
            self._ps.plot_antenna_positions()
        return self._ps.get_combined_antenna_xds().antenna_name.values.tolist()

    def plot_phase_centers(self, label_all_fields=False, data_group='base'):
        ''' Plot the phase center locations of all fields in the Processing Set and label central field.
                label_all_fields (bool); label all fields on the plot
                data_group (str); data group to use for processing.
        '''
        self._ps.plot_phase_centers(label_all_fields, data_group)

    def clear_plots(self):
        self._plots.clear()

    def show(self, title='MsPlot', port=0, layout=None):
        ''' 
        Show interactive Bokeh plots in a browser.  Plot tools include pan, zoom, hover, and save.
        Multiple plots can be displayed in a panel layout. Default will show first plot only.
            title (str): browser tab title.
            port (int): allows specifying port number.
            layout (tuple): (start, rows, columns) settings for multiple plots.
        '''
        if not self._plots:
            raise RuntimeError("No plots to show.  Run plot() to create plot.")

        # Single plot or combine plots into layout
        layout = (0, 1, 1) if layout is None else layout 
        plot, is_layout = self._layout_plots(layout)

        if is_layout:
            # Show plots in columns
            hvplot.show(plot.cols(layout[2]), title=title, threaded=True)
        else:
            # Show single plot
            hvplot.show(plot.opts(width=900, height=600), title=title, threaded=True)

    def save(self, filename='ms_plot.png', fmt='auto', layout=None, export_range='one'):
        '''
        Save plot to file.
            filename (str): Name of file to save.
            fmt (str): Format of file to save ('png', 'svg', 'html', or 'gif') or 'auto': inferred from filename.
            layout (tuple): panel layout settings (start, rows, columns) for multiple plots.
            exprange (str): whether to save starting plot only ('one') or all plots starting at starting plot ('all') with index in filename. Ignored if layout is a grid.

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
                plot = self._plots[i].opts(height=600, width=900)
                if export_range == 'all' and num_plots > 1:
                    exportname = f"{name}_{i}{ext}"
                else:
                    exportname = filename
                hvplot.save(plot, filename=exportname, fmt=fmt)
                self._logger.info(f"Saved plot to {exportname}.")

        self._logger.debug(f"Save elapsed time: {time.time() - start:.3f} s.")

    def _get_unique_values(self, df):
        values = df.to_numpy()
        try:
            # numeric arrays
            return np.unique(np.concatenate(values))
        except ValueError:
            # string arrays
            all_values = [row[0] for row in values]
            return np.unique(np.concatenate(all_values))

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

        # Combine plots into layout
        num_combined_plots = 0
        combined_plot = None
        for i in range(start, start + num_layout_plots):
            if i >= num_plots:
                break
            plot = self._plots[i]
            combined_plot = plot if combined_plot is None else combined_plot + plot
            num_combined_plots += 1
        return combined_plot, num_layout_plots > 1
