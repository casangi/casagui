'''
Utility functions to manage ps data
'''
import numpy as np
from pandas import to_datetime
import xarray as xr

def select_ps(ps, selection, do_select_ddi):
    ''' Return processing set per ddi containing selected field, and intent.
        If ddi is selected here, it is added to selection dict.
        Raise exception if selection is invalid. '''
    ddi = selection['ddi'] if (selection is not None and 'ddi' in selection.keys()) else None
    field = selection['field'] if (selection is not None and 'field' in selection.keys()) else None
    intent = selection['intent'] if (selection is not None and 'intent' in selection.keys()) else None
    if ddi is not None or field is not None or intent is not None:
        print(f"Processing set selection: ddi={ddi} field={field} intent={intent}")

    # Apply ddi selection to make ddi list
    ps_ddis = sorted(set(ps.summary()['ddi']))
    if ddi is None:
        if do_select_ddi:
            ddi = ps_ddis[0]
            print(f"No ddi selected, using first ddi: {ddi}.")
            if selection is None:
                selection = {'ddi': ddi}
            else:
                selection['ddi'] = ddi
    else:
        if ddi not in ps_ddis:
            raise ValueError(f"Invalid ddi selection {ddi}. Please select from {ps_ddis}.")

    plot_ps = {}
    for key in ps:
        xds = ps[key]

        # ddi selection
        if ddi is None:
            has_selected_ddi = True # default all ddis
            # Make ddi a data dimension
            xds = xds.expand_dims(dim={"ddi": np.array(ps_ddis)}, axis=0)
        else:
            if isinstance(ddi, int):
                has_selected_ddi = (xds.attrs['ddi'] == ddi)
                xds = xds.expand_dims(dim={"ddi": np.array([ddi])}, axis=0)
            elif isinstance(ddi, list):
                has_selected_ddi = xds.attrs['ddi'] in ddi
                xds = xds.expand_dims(dim={"ddi": np.array(ddi)}, axis=0)

        if has_selected_ddi:
            # field selection
            if field is None:
                has_selected_field = True # default all fields
            else:
                field_info = xds.VISIBILITY.field_info
                if isinstance(field, int):
                    has_selected_field = (field_info['field_id'] == field)
                elif isinstance(field, str):
                    has_selected_field = (field_info['name'] == field)
                elif isinstance(field, list):
                    has_selected_field = (field_info['name'] in field or
                                          field_info['field_id'] in field
                    )
                else:
                    raise ValueError("Invalid type for field selection, must select by id or name")

            if has_selected_field:
                # intent selection
                if intent is None:
                    has_selected_intent = True # default all intents
                elif isinstance(intent, str):
                    has_selected_intent = (xds.intent == intent)
                elif isinstance(intent, list):
                    has_selected_intent = xds.intent in intent

                if has_selected_intent:
                    # passed all checks
                    plot_ps[key] = xds

    return plot_ps, selection

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

def get_coordinate_label(xds, coordinate):
    ''' Return coordinate value as string '''
    label = get_coordinate_labels(xds, coordinate)[0][1]
    if coordinate == 'time':
        date = _get_date_string(xds.time)
        return f"{date} {label}"
    elif coordinate == 'frequency':
        return f"{label} {xds.frequency.attrs['units']}"
    return label

def get_coordinate_labels(xds, coordinate):
    ''' Return coordinate values as numeric array or list of (index, str) labels '''
    if coordinate == 'time':
        return _get_time_labels(xds.time)
    elif coordinate == 'baseline_id':
        return _get_baseline_labels(xds)
    elif coordinate == 'frequency':
        return _get_frequency_labels(xds.frequency)
    elif coordinate == 'polarization':
        return _get_polarization_labels(xds.polarization)
    elif coordinate == 'ddi':
        return _get_ddi_labels(xds.ddi)

def _get_time_labels(time_xda):
    ''' Return list of (index, time string) '''
    times = to_datetime(time_xda, unit='s').strftime("%H:%M:%S")
    if isinstance(times, str):
        return [(0, times)]
    return list(enumerate(times.values))

def _get_baseline_labels(xds):
    ''' Return list of (index, ant1@station) for each new ant1 in baseline.
        If single baseline, use ant1@station & ant2@station '''
    baseline_labels = []
    antenna_names = _get_antenna_names(xds.antenna_xds)
    baseline_pairs = _get_baseline_pairs(xds.antenna_xds.antenna_id.size)
    baseline_ids = xds.baseline_id.values

    if baseline_ids.size == 1:
        ant1, ant2 = baseline_pairs[baseline_ids]
        return [(0, f"{antenna_names[ant1]} & {antenna_names[ant2]}")]

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
    ''' Return list of (index, polarization) '''
    if polarization_xda.size == 1:
        return [(0, polarization_xda.values)]
    return list(enumerate(polarization_xda.values))

def _get_frequency_labels(frequency_xda):
    ''' Return list of (index, frequency) or None to autogenerate ticks '''
    if frequency_xda.size == 1:
        return [(0, f"{frequency_xda.values:.5f}")]
    else:
        return None # auto ticks from frequency values

def _get_ddi_labels(ddi_xda):
    ''' Return list of (index, ddi) or None to autogenerate ticks '''
    if ddi_xda.size == 1:
        return [(0, f"{ddi_xda.values}")]
    else:
        return None # auto ticks from ddi values

def set_frequency_unit(xds):
    ''' Set unit as string (not list) and convert to GHz if Hz '''
    unit = xds.frequency.attrs['units']
    if isinstance(unit, list):
        unit = unit[0]

    if unit == 'Hz':
        xds['frequency'] = xds.frequency / 1.0e9
        xds['frequency'] = xds.frequency.assign_attrs(units='GHz')
    else:
        xds['frequency'] = xds.frequency.assign_attrs(units=unit)

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
        xds['baseline_id'] = np.array(range(xds.baseline_id.size))
    elif axis == "frequency":
        unit = xds.frequency.frequency.attrs['units']
        label =  f"Frequency ({unit})"
    elif axis == "polarization":
        label =  "Polarization"
        xds['polarization'] = np.array(range(xds.polarization.size))
    elif axis == "ddi":
        label =  "DDI"
    return (axis, label, ticks)

def _get_date_string(time_xda):
    ''' Return date as dd-Mon-yyyy e.g. 23-Aug-2010 '''
    if time_xda.size == 1:
        return to_datetime(time_xda.values, unit=time_xda.units[0]).strftime("%d-%b-%Y")
    else:
        return to_datetime(time_xda.values[0], unit=time_xda.units[0]).strftime("%d-%b-%Y")
