'''
Utility functions to manage xradio processing_set
'''

import pandas as pd

from xradio.vis._processing_set import processing_set

def summary(ps, columns=None):
    ''' Print processing set summary.
        Args:
            ps (processing_set): ps for summary
            columns (None, str, list): type of metadata to list.
                None:      Print all summary columns in processing set.
                'by_msv4': Print formatted summary metadata by MSv4.
                str, list: Print a subset of summary columns in processing set.
                    Options include 'name', 'obs_mode', 'shape', 'polarization', 'spw_name', 'field_name', 'source_name', 'field_coords', 'start_frequency', 'end_frequency'
    '''
    pd.set_option("display.max_rows", len(ps))
    pd.set_option("display.max_columns", 12)
    ps_summary = ps.summary()

    if columns is None:
        print(ps_summary)
    elif columns == "by_msv4":
        for row in ps_summary.itertuples(index=False):
            name, obs_mode, shape, polarization, scan_number, spw_name, field_name, source_name, line_name, field_coords, start_frequency, end_frequency = row
            print("-----")
            print(f"MSv4 name: {name}")
            print(f"obs_mode: {obs_mode}")
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
        columns_in_list = []
        for column in columns:
            if column in ps_summary.columns:
                columns_in_list.append(column)
            else:
                print(f"Ignoring invalid summary column: {column}")
        print(ps_summary[columns_in_list])
