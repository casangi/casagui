''' Define constants used for plotting MeasurementSets '''

SPECTRUM_AXIS_OPTIONS = ['amp', 'real']
UVW_AXIS_OPTIONS = ['u', 'v', 'w', 'uvdist']
VIS_AXIS_OPTIONS = ['amp', 'phase', 'real', 'imag']
WEIGHT_AXIS_OPTIONS = ['weight', 'sigma']

PS_SELECTION_OPTIONS = {
    'MSv4 Name': 'name',
    'Intents': 'intents',
    'Scan Name': 'scan_name',
    'Spectral Window Name': 'spw_name',
    'Field Name': 'field_name',
    'Source Name': 'source_name',
    'Line Name': 'line_name'
}
MS_SELECTION_OPTIONS = ['Data Group', 'Time', 'Baseline', 'Antenna1', 'Antenna2', 'Frequency', 'Polarization']

AGGREGATOR_OPTIONS = ['None', 'max', 'mean', 'median', 'min', 'std', 'sum', 'var']

DEFAULT_UNFLAGGED_CMAP = "Viridis"
DEFAULT_FLAGGED_CMAP = "Reds"
