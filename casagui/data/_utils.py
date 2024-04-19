'''
Utility functions to manage ps data
'''
import numpy as np
from pandas import to_datetime
import xarray as xr

def get_ddi_ps(ps, selection):
    ''' Return processing set containing selected ddi, field, and/or intent only.
        Raise exception if selection is invalid. '''
    ddi = selection['ddi'] if (selection is not None and 'ddi' in selection.keys()) else None
    field = selection['field'] if (selection is not None and 'field' in selection.keys()) else None
    intent = selection['intent'] if (selection is not None and 'intent' in selection.keys()) else None
    if ddi is not None or field is not None or intent is not None:
        print(f"Metadata selection: ddi={ddi} field={field} intent={intent}")

    # Check ddi selection
    ddi_list = sorted(set(ps.summary()['ddi']))
    if ddi is None:
        ddi = ddi_list[0]
        print(f"No ddi selected, using first ddi: {ddi}.")
    elif ddi not in ddi_list:
        raise ValueError(f"Invalid ddi selection {ddi}. Please select from {ddi_list}.")

    ddi_ps = {}
    for key in ps:
        xds = ps[key]
        if xds.ddi == ddi:
            # Check field selection
            if field is None:
                selected_field = True # default all fields
            else:
                selected_field = False
                field_info = xds.VISIBILITY.field_info
                if isinstance(field, int):
                    selected_field = (field_info['field_id'] == field)
                elif isinstance(field, str):
                    selected_field = (field_info['name'] == field)
                elif isinstance(field, list):
                    selected_field = (field_info['name'] in field or
                                      field_info['field_id'] in field
                    )
                else:
                    raise ValueError("Invalid type for field selection, must select by id or name")

            if selected_field:
                # Check intent selection (default all intents)
                if intent is None:
                    selected_intent = True # default all intents
                elif xds.intent == intent:
                    selected_intent = True
                else:
                    selected_intent = False

                if selected_field and selected_intent:
                    # passed all checks
                    ddi_ps[key] = xds
    return ddi_ps

def concat_ps_xds(ps):
    ''' Concatenate xarray Datasets in processing set '''
    xds_list = [ps[key] for key in ps]

    if len(xds_list) == 0:
        raise RuntimeError("Metadata selection resulted in no datasets.")

    print("Plotting", len(xds_list), "msv4 datasets.")
    return xr.concat(xds_list, dim='time')

def _get_baseline_pairs(n_antennas):
    baselines = []
    for i in range(n_antennas):
        for j in range(i, n_antennas):
            baselines.append((i, j))
    return baselines

def set_baseline_ids(xds):
    ''' Set baseline id coordinate according to each ant1&ant2 pair '''
    baseline_pairs = _get_baseline_pairs(xds.antenna_xds.antenna_id.size)
    ant1 = xds.baseline_antenna1_id.values
    ant2 = xds.baseline_antenna2_id.values
    new_baseline_ids = []
    for idx in xds.baseline_id.values:
        try:
            new_id = baseline_pairs.index((ant1[idx], ant2[idx]))
        except ValueError:
            new_id = np.nan
        new_baseline_ids.append(new_id)
    xds["baseline_id"] = np.array(new_baseline_ids)

def get_coordinate_labels(xds, coordinate):
    if coordinate == 'time':
        return _get_time_labels(xds.coords[coordinate])
    elif coordinate == 'baseline_id':
        return _get_baseline_labels(xds)
    elif coordinate == 'frequency':
        return _get_frequency_labels(xds.coords[coordinate])
    else:
        return _get_polarization_labels(xds.coords[coordinate])

def _get_time_labels(time_xda):
    ''' Return single timestamp or list of (index, time string) '''
    times = to_datetime(time_xda, unit='s').strftime("%H:%M:%S")
    if isinstance(times, str):
        date = _get_date_string(time_xda)
        return date + " " + times
    return list(enumerate(times.values))

def _get_baseline_labels(xds):
    ''' Return single ant1@ant2 or list of (index, ant1 name) for each new ant1 in baseline '''
    baseline_labels = []
    antenna_names = _get_antenna_names(xds.antenna_xds)
    baseline_pairs = _get_baseline_pairs(xds.antenna_xds.antenna_id.size)
    baseline_ids = xds.baseline_id.values

    if baseline_ids.size == 1:
        ant1, ant2 = baseline_pairs[baseline_ids]
        return f"{antenna_names[ant1]} & {antenna_names[ant2]}"

    last_ant1 = None
    last_idx = None
    increment = len(antenna_names) / 3 

    # Add label for every new ant1 if there is room (increment)
    for idx, baseline_id in enumerate(baseline_ids):
        ant1, ant2 = baseline_pairs[baseline_id]
        if ant1 != last_ant1:
            last_ant1 = ant1
            if last_idx is None:
                baseline_labels.append((idx, antenna_names[ant1]))
                last_idx = idx
            else:
                if (idx - last_idx) >= increment:
                    baseline_labels.append((idx, antenna_names[ant1]))
                    last_idx = idx
    return baseline_labels

def _get_antenna_names(antenna_xds):
    ''' Return lists of antenna names (antenna@station) '''
    names = antenna_xds.name.values
    stations = antenna_xds.station.values
    antennas = [f"{names[i]}@{stations[i]}" for i in range(len(names))]
    return antennas

def _get_polarization_labels(polarization_xda):
    if polarization_xda.size == 1:
        return polarization_xda.values
    else:
        return list(enumerate(polarization_xda.values))

def _get_frequency_labels(frequency_xda):
    if frequency_xda.size == 1:
        return f"{frequency_xda.values:.3f} {frequency_xda.attrs['units']}"
    else:
        return None
    #freq_labels = [f"{f:.3f}" for f in frequency_xda.values]
    #return list(enumerate(freq_labels))

def set_frequency_unit(xds):
    # Set unit as string (not list) and convert to GHz if Hz
    unit = xds.frequency.attrs['units']
    if isinstance(unit, list):
        unit = unit[0]

    if unit == 'Hz':
        xds['frequency'] = xds.frequency / 1.0e9
        xds['frequency'] = xds.frequency.assign_attrs(units='GHz')
    else:
        xds['frequency'] = xds.frequency.assign_attrs(units=unit)

def get_vis_axis_label(xda, axis):
    ''' Get vis axis label for colorbar '''
    label = axis.capitalize()
    if 'units' in xda.attrs:
        unit = xda.attrs['units']
        label += f" ({unit})"
    return label

def get_axis_labels(xds, axis):
    ''' Return axis name, label and ticks, reindex for regular axis '''
    ticks = get_coordinate_labels(xds, axis)

    if axis == "time":
        date = _get_date_string(xds.time) 
        label =  f"Time ({date})"
        if xds.time.size > 1:
            tick_inc = int(len(ticks) / 10)
            ticks = ticks[::tick_inc]
            xds['time'] = np.array(range(xds.time.size))
    elif axis == "baseline_id":
        label = "Baseline Antenna1"
        if xds.baseline_id.size > 1:
            xds['baseline_id'] = np.array(range(xds.baseline_id.size))
    elif axis == "frequency":
        unit = xds.frequency.frequency.attrs['units']
        label =  f"Frequency ({unit})"
    else:
        label =  "Correlation"
        if xds.polarization.size > 1:
            xds['polarization'] = np.array(range(xds.polarization.size))
    return (axis, label, ticks)

def _get_date_string(time_xda):
    if time_xda.size == 1:
        return to_datetime(time_xda.values, unit=time_xda.units[0]).strftime("%d-%b-%Y")
    else:
        return to_datetime(time_xda.values[0], unit=time_xda.units[0]).strftime("%d-%b-%Y")
