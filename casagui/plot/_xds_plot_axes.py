'''
Functions for plot axes labels
'''

# pylint: disable=inconsistent-return-statements
def get_coordinate_labels(xds, coordinate):
    ''' Return coordinate values as string or list of strings, or None if numeric '''
    if coordinate == 'time':
        return _get_time_labels(xds.time)
    if coordinate == 'baseline':
        return _get_baseline_antenna_labels(xds.baseline)
    if coordinate == 'antenna_name':
        return _get_baseline_antenna_labels(xds.antenna_name)
    if coordinate == 'frequency':
        return _get_frequency_labels(xds.frequency)
    if coordinate == 'polarization':
        return _get_polarization_labels(xds.polarization)
# pylint: enable=inconsistent-return-statements

def get_axis_labels(xds, axis):
    ''' Return axis name, label and ticks, reindex for regular axis '''
    labels = get_coordinate_labels(xds, axis)
    ticks = list(enumerate(labels)) if labels is not None and isinstance(labels, list) else None

    if axis == "time":
        start_date, _ = _get_date_range(xds.time)
        label =  f"Time {xds.time.attrs['scale'].upper()} ({start_date})"
    elif axis == "baseline":
        label = "Baseline Antenna1"
        ticks = _get_baseline_ant1_ticks(ticks)
    elif axis == "antenna_name":
        label = "Antenna"
    elif axis == "frequency":
        label = f"Frequency ({xds.frequency.attrs['units']}) {xds.frequency.attrs['observer'].upper()}"
    elif axis == "polarization":
        label =  "Polarization"
    else:
        label = None
    return (axis, label, ticks)

def get_vis_axis_labels(xds, data_group, correlated_data, vis_axis, include_unit=True):
    ''' Get vis axis label for colorbar. Returns (axis, label, ticks) '''
    label = vis_axis.capitalize()
    if data_group != 'base':
        label += f":{data_group.capitalize()}"

    if include_unit:
        units = None
        if vis_axis in xds.data_vars and 'units' in xds[vis_axis].attrs:
            units = xds[vis_axis].units
        else:
            if 'units' in xds[correlated_data].attrs:
                units = xds[correlated_data].units
        if units:
            label += f" ({units})"

    return (vis_axis, label)

def _get_time_labels(time_xda):
    ''' Return time as formatted string, or None to autogenerate ticks '''
    if time_xda.size == 1:
        time = time_xda.values.astype('datetime64[s]').item().strftime("%d-%b-%Y %H:%M:%S")
        time += " " + time_xda.attrs['scale'].upper()
        return time
    return None # auto ticks from time values

def _get_baseline_antenna_labels(baseline_antenna_xda):
    ''' Return baseline pairs as string or list of strings '''
    if baseline_antenna_xda.size == 1:
        return baseline_antenna_xda.values
    return baseline_antenna_xda.values.ravel().tolist()

def _get_polarization_labels(polarization_xda):
    ''' Return polarization as single string or list of strings '''
    if polarization_xda.size == 1: # string
        return polarization_xda.values
    return list(polarization_xda.values) # array of strings

def _get_frequency_labels(frequency_xda):
    ''' Return frequency as formatted string, or None to autogenerate ticks '''
    if frequency_xda.size == 1:
        return f"{frequency_xda.item():.4f} {frequency_xda.attrs['units']} {frequency_xda.attrs['observer'].upper()}"
    return None # auto ticks from frequency values

def _get_date_range(time_xda):
    ''' Return date as dd-Mon-yyyy e.g. 23-Aug-2010 '''
    if time_xda.size == 1:
        date = time_xda.values.astype('datetime64[s]').item().strftime("%d-%b-%Y")
        return (date, date)
    start_date = time_xda.values[0].astype('datetime64[s]').item().strftime("%d-%b-%Y")
    end_date = time_xda.values[time_xda.size - 1].astype('datetime64[s]').item().strftime("%d-%b-%Y")
    return (start_date, end_date)

def _get_baseline_ant1_ticks(baseline_ticks):
    ''' Return labels for each new ant1 name in baselines '''
    ant1_ticks = []
    last_ant1 = None
    last_idx = None

    # space by minimum increment to avoid overlapping tick labels
    min_increment = max(int(len(baseline_ticks) / 50), 1)

    for idx, tick in baseline_ticks:
        ant1_name = tick.split(' & ')[0]
        if ant1_name != last_ant1:
            last_ant1 = ant1_name
            if last_idx is None or ((idx - last_idx) >= min_increment):
                ant1_ticks.append((idx, ant1_name))
                last_idx = idx
    return ant1_ticks
