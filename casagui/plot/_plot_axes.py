'''
Functions for plot axes labels
'''
import numpy as np
from pandas import to_datetime

def get_coordinate_label(xds, coordinate):
    ''' Return single coordinate value as string '''
    label = get_coordinate_labels(xds, coordinate)
    if coordinate == 'time':
        date = _get_date_string(xds.time)
        label = f"{date} {label}"
    elif coordinate == 'frequency':
        label = f"{label} {xds.frequency.attrs['units']}"
    return label

def get_coordinate_labels(xds, coordinate):
    ''' Return coordinate values as list of string labels or None if numeric '''
    if coordinate == 'time':
        return _get_time_labels(xds.time)
    elif coordinate == 'baseline':
        return _get_baseline_labels(xds.baseline)
    elif coordinate == 'frequency':
        return _get_frequency_labels(xds.frequency)
    elif coordinate == 'polarization':
        return _get_polarization_labels(xds.polarization)
    elif coordinate == 'ddi':
        return _get_ddi_labels(xds.ddi)

def _get_time_labels(time_xda):
    ''' Return time string or list of time strings '''
    times = to_datetime(time_xda, unit='s').strftime("%H:%M:%S")
    if isinstance(times, str):
        return times
    return list(times.values)

def _get_baseline_labels(baseline_xda):
    ''' Return baseline string or list of strings '''
    if baseline_xda.size == 1: # string
        return baseline_xda.values
    return list(baseline_xda.values) # array of strings

def _get_polarization_labels(polarization_xda):
    ''' Return polarization string or list of polarization strings '''
    if polarization_xda.size == 1: # string
        return polarization_xda.values
    return list(polarization_xda.values) # array of strings

def _get_frequency_labels(frequency_xda):
    ''' Return frequency string for single value, or None to autogenerate ticks '''
    if frequency_xda.size == 1: # float
        return f"{frequency_xda.values:.5f}"
    else:
        return None # auto ticks from frequency values

def _get_ddi_labels(ddi_xda):
    ''' Return ddi string for single value, or None to autogenerate ticks '''
    if ddi_xda.size == 1: # int
        return f"{ddi_xda.values[0]}"
    else:
        return None # auto ticks from ddi values

def get_vis_axis_labels(xda, axis):
    ''' Get vis axis label for colorbar '''
    name = axis.capitalize()
    label = name
    if 'units' in xda.attrs:
        unit = xda.attrs['units']
        label += f" ({unit})"
    return (name, label)

def get_axis_labels(xds, axis):
    ''' Return axis name, label and ticks, reindex for regular axis '''
    labels = get_coordinate_labels(xds, axis)
    ticks = list(enumerate(labels)) if labels is not None else None

    if axis == "time":
        date = _get_date_string(xds.time) 
        label =  f"Time ({date})"
        if xds.time.size > 1:
            tick_inc = int(len(ticks) / 10)
            ticks = ticks[::tick_inc]
        xds = xds.assign_coords(timestamp=("time", np.array(labels)))
        xds['time'] = np.array(range(xds.time.size)) # index
    elif axis == "baseline":
        label = "Baseline Antenna1"
        # Use only ticks with new antenna1 and minimum increment of 3
        ticks = _get_baseline_ant1_ticks(ticks, 3)
        xds['baseline'] = np.array(range(xds.baseline.size)) # index
    elif axis == "frequency":
        unit = xds.frequency.frequency.attrs['units']
        label =  f"Frequency ({unit})"
    elif axis == "polarization":
        label =  "Polarization"
        xds['polarization'] = np.array(range(xds.polarization.size)) # index
    elif axis == "ddi":
        label =  "DDI"
    return xds, (axis, label, ticks)

def _get_date_string(time_xda):
    ''' Return date as dd-Mon-yyyy e.g. 23-Aug-2010 '''
    if time_xda.size == 1:
        return to_datetime(time_xda.values, unit=time_xda.units[0]).strftime("%d-%b-%Y")
    else:
        return to_datetime(time_xda.values[0], unit=time_xda.units[0]).strftime("%d-%b-%Y")

def _get_baseline_ant1_ticks(baselines, min_increment):
    ''' Return labels for each new ant1 name, spaced by minimum increment '''
    baseline_ticks = []
    last_ant1 = None
    last_idx = None

    for idx, baseline in baselines:
        ant1_name = baseline.split(' & ')[0]
        if ant1_name != last_ant1:
            last_ant1 = ant1_name
            if last_idx is None or ((idx - last_idx) >= min_increment):
                baseline_ticks.append((idx, ant1_name))
                last_idx = idx
    return baseline_ticks
