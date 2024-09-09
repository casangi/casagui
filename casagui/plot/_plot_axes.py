'''
Functions for plot axes labels
'''
import numpy as np
from pandas import to_datetime
import xarray as xr

def get_coordinate_label(xds, coordinate):
    ''' Return single coordinate value as string '''
    label = _get_coordinate_labels(xds, coordinate)
    if coordinate == 'frequency':
        label = f"{label} {xds.frequency.attrs['units']}"
    return label

def _get_coordinate_labels(xds, coordinate):
    ''' Return coordinate values as list of string labels or None if numeric '''
    if coordinate == 'time':
        return _get_time_labels(xds.time)
    elif coordinate == 'baseline':
        return _get_baseline_antenna_labels(xds.baseline)
    elif coordinate == 'antenna_name':
        return _get_baseline_antenna_labels(xds.antenna_name)
    elif coordinate == 'frequency':
        return _get_frequency_labels(xds.frequency)
    elif coordinate == 'polarization':
        return _get_polarization_labels(xds.polarization)
    elif coordinate == 'spw':
        return _get_spw_labels(xds.spw)

def _get_time_labels(time_xda):
    ''' Return time string or list of time strings '''
    if time_xda.size > 1:
        times = to_datetime(time_xda, unit='s').strftime("%H:%M:%S")
    else:
        times = to_datetime(time_xda, unit='s').strftime("%d-%b-%Y %H:%M:%S")
    return times if isinstance(times, str) else list(times.values)

def _get_baseline_antenna_labels(baseline_antenna_xda):
    ''' Return baseline pair string or list of strings '''
    if baseline_antenna_xda.size == 1:
        return baseline_antenna_xda.values
    return baseline_antenna_xda.values.ravel().tolist()

def _get_polarization_labels(polarization_xda):
    ''' Return polarization string or list of polarization strings '''
    if polarization_xda.size == 1: # string
        return polarization_xda.values
    return list(polarization_xda.values) # array of strings

def _get_frequency_labels(frequency_xda):
    ''' Return frequency string for single value, or None to autogenerate ticks '''
    if frequency_xda.size == 1:
        return f"{frequency_xda.values:.4f}"
    else:
        return None # auto ticks from frequency values

def _get_spw_labels(spw_xda):
    ''' Return ddi string for single value, or None to autogenerate ticks '''
    if spw_xda.size == 1: # int
        return f"{spw_xda.values[0]}"
    else:
        return None # auto ticks from spw values

def get_vis_axis_labels(xds, data_var, axis):
    ''' Get vis axis label for colorbar '''
    try:
        name, data_type = axis.split('_')
    except ValueError:
        name = axis
        data_type = None

    label = f"{data_type.capitalize()} " if data_type else ''
    label += name.capitalize()

    if 'units' in xds[data_var].attrs:
        label += f" ({xds[data_var].attrs['units']})"
    return (name, label)

def get_axis_labels(xds, axis):
    ''' Return axis name, label and ticks, reindex for regular axis '''
    labels = _get_coordinate_labels(xds, axis)
    ticks = list(enumerate(labels)) if labels is not None else None

    if axis == "time":
        start_date, end_date = _get_date_range(xds.time)
        label =  f"Time ({start_date})"
        if xds.time.size > 1:
            tick_inc = max(int(len(ticks) / 10), 1)
            ticks = ticks[::tick_inc]
        # Set time axis as time index
        xds['time'] = np.array(range(xds.time.size))
        xds['timestamp'] = xr.DataArray(np.array(labels), dims=xds.time.dims)
    elif axis == "baseline":
        label = "Baseline Antenna1"
        ticks = _get_baseline_ant1_ticks(ticks)
        xds['baseline'] = np.array(range(xds.baseline.size))
    elif axis == "antenna_name":
        label = "Antenna"
        xds['antenna_name'] = np.array(range(xds.antenna_name.size))
    elif axis == "frequency":
        unit = xds.frequency.frequency.attrs['units']
        label =  f"Frequency ({unit})"
    elif axis == "polarization":
        label =  "Polarization"
        # replace axis with index for plot range
        xds['polarization'] = np.array(range(xds.polarization.size))
    elif axis == "spw":
        label =  "Spectral Window"
    return xds, (axis, label, ticks)

def _get_date_range(time_xda):
    ''' Return date as dd-Mon-yyyy e.g. 23-Aug-2010 '''
    if time_xda.size == 1:
        date = time_xda.values.astype('datetime64[s]').item().strftime("%d-%b-%Y")
        return (date, date)
    else:
        start_date = time_xda.values[0].astype('datetime64[s]').item().strftime("%d-%b-%Y")
        end_date = time_xda.values[time_xda.size - 1].astype('datetime64[s]').item().strftime("%d-%b-%Y")
        return (start_date, end_date)

def _get_baseline_ant1_ticks(baseline_ticks):
    ''' Return labels for each new ant1 name '''
    # space by minimum increment to avoid overlapping tick labels
    min_increment = max(int(len(baseline_ticks) / 50), 1)
    ant1_ticks = []
    last_ant1 = None
    last_idx = None

    for idx, tick in baseline_ticks:
        ant1_name = tick.split(' & ')[0]
        if ant1_name != last_ant1:
            last_ant1 = ant1_name
            if last_idx is None or ((idx - last_idx) >= min_increment):
                ant1_ticks.append((idx, ant1_name))
                last_idx = idx
    return ant1_ticks
