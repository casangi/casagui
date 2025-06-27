''' Define constants used for plotting MeasurementSets '''

SPECTRUM_AXIS_OPTIONS = ['amp', 'real']
UVW_AXIS_OPTIONS = ['u', 'v', 'w', 'uvdist']
VIS_AXIS_OPTIONS = ['amp', 'phase', 'real', 'imag']
WEIGHT_AXIS_OPTIONS = ['weight', 'sigma']

# GUI label to selection keyword
PS_SELECTION_OPTIONS = {
    'MSv4 Name': 'name',
    'Intents': 'intents',
    'Scan Name': 'scan_name',
    'Spectral Window Name': 'spw_name',
    'Field Name': 'field_name',
    'Source Name': 'source_name',
    'Line Name': 'line_name'
}

MS_SELECTION_OPTIONS = {
    'Data Group': 'data_group',
    'Time': 'time',
    'Baseline': 'baseline',
    'Antenna1': 'antenna1',
    'Antenna2': 'antenna2',
    'Frequency': 'frequency',
    'Polarization': 'polarization'
}

AGGREGATOR_OPTIONS = ['None', 'max', 'mean', 'median', 'min', 'std', 'sum', 'var']

DEFAULT_UNFLAGGED_CMAP = "Viridis"
DEFAULT_FLAGGED_CMAP = "Reds"
