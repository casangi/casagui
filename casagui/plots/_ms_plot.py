'''
Common functions for ms raster and scatter plots
'''

import hvplot
import pandas as pd

from xradio.measurement_set.processing_set import ProcessingSet

def print_summary(ps, columns):
    ''' Print ProcessingSet summary.
        Args:
            ps (xradio ProcessingSet): ps for summary
            columns (None, str, list): type of metadata to list.
                None:      Print all summary columns in ProcessingSet.
                'by_msv4': Print formatted summary metadata by MSv4.
                str, list: Print a subset of summary columns in ProcessingSet.
                    Options include 'name', 'intents', 'shape', 'polarization', 'scan_number', 'spw_name', 'field_name', 'source_name', 'field_coords', 'start_frequency', 'end_frequency'
    '''
    pd.set_option("display.max_rows", len(ps))
    pd.set_option("display.max_columns", 12)
    ps_summary = ps.summary()

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

def get_data_groups(ps):
    ''' Get data groups from all ProcessingSet ms_xds. Returns set. '''
    data_groups = []
    for xds_name in ps:
        data_groups.extend(list(ps[xds_name].attrs['data_groups']))
    return set(data_groups)

def list_data_groups(ps, logger):
    ''' Print data groups from all ProcessingSet ms_xds '''
    logger.info(f"Processing set data groups: {get_data_groups(ps)}")

def list_antennas(ps, logger, plot_positions):
    ''' Print antenna names in ProcessingSet antenna_xds, optionally plot antenna positions '''
    antenna_names = ps.get_combined_antenna_xds().antenna_name.values.tolist()
    logger.info(f"Antenna names: {antenna_names}")
    if plot_positions:
        ps.plot_antenna_positions()

def show(plot, title):
    ''' 
    Show interactive Bokeh plot in a browser.
    Plot tools include pan, zoom, hover, and save.
    Groupby axes have selectors: slider, dropdown, etc.
    '''
    if plot is None:
        raise RuntimeError("No plot to show.  Run plot() to create plot.")
    hvplot.show(plot, title=title, threaded=True)


def save(plot, filename, fmt, hist, backend, resources, toolbar, title):
    '''
    Save plot to file.
        filename (str): Name of file to save.
        fmt (str): Format of file to save ('png', 'svg', 'html', or 'gif') or 'auto': inferred from filename.
        hist (bool): Whether to compute and adjoin histogram.
        backend (str): rendering backend, 'bokeh' or 'matplotlib'.
        resources (str): whether to save with 'online' or 'offline' resources.  'offline' creates a larger file.
        toolbar (bool): Whether to include the toolbar in the exported plot.
        title (str): Custom title for exported HTML file.
    '''
    if plot is None:
        raise RuntimeError("No plot to save.  Run plot() to create plot.")

    # embed BokehJS resources inline for offline use, else use content delivery network
    resources = 'inline' if resources == 'offline' else 'cdn'

    if hist:
        hvplot.save(plot.hist(), filename=filename, fmt=fmt, backend=backend, resources=resources, toolbar=toolbar, title=title)
    else:
        hvplot.save(plot, filename=filename, fmt=fmt, backend=backend, resources=resources, toolbar=toolbar, title=title)
