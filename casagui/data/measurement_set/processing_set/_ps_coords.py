'''
Modify/add xarray Dataset coordinates for plotting.
'''

import numpy as np
from pandas import to_datetime

def set_coordinates(ms_xdt):
    ''' Convert coordinate units and add baseline coordinate for plotting.
        Returns xarray.Dataset
    '''
    _set_coordinate_unit(ms_xdt)
    _set_frequency_unit(ms_xdt)
    return _add_baseline_coordinate(ms_xdt)

def set_datetime_coordinate(ms_xds):
    ''' Convert float time to datetime for plotting. '''
    time_attrs = ms_xds.time.attrs
    try:
        ms_xds.coords['time'] = to_datetime(ms_xds.time, unit=time_attrs['units'], origin=time_attrs['format'])
    except TypeError:
        ms_xds.coords['time'] = to_datetime(ms_xds.time, unit=time_attrs['units'][0], origin=time_attrs['format'])
    ms_xds.time.attrs = time_attrs

def _set_coordinate_unit(ms_xdt):
    ''' Set coordinate units attribute as string not list for plotting. '''
    for coord in ms_xdt.coords:
        # Plots need unit to be string not list
        if 'units' in ms_xdt.coords[coord].attrs:
            units = ms_xdt.coords[coord].units
            if isinstance(units, list) and len(units) == 1:
                ms_xdt.coords[coord].attrs['units'] = units[0]

def set_index_coordinates(ms_xds, coordinates):
    ''' Return ms_xds with new coordinate for string values (name) then replace coordinate with numerical index. '''
    for coordinate in coordinates:
        if coordinate == "polarization":
            ms_xds = ms_xds.assign_coords({"polarization_name": (ms_xds.polarization.dims, ms_xds.polarization.values)})
            ms_xds["polarization"] = np.array(range(ms_xds.polarization.size))
        elif coordinate == "baseline":
            ms_xds = ms_xds.assign_coords({"baseline_name": (ms_xds.baseline.dims, ms_xds.baseline.values)})
            ms_xds["baseline"] = np.array(range(ms_xds.baseline.size))
        elif coordinate == "antenna_name":
            ms_xds = ms_xds.assign_coords({"antenna": (ms_xds.antenna_name.dims, ms_xds.antenna_name.values)})
            ms_xds["antenna_name"] = np.array(range(ms_xds.antenna_name.size))
    return ms_xds

def _set_frequency_unit(ms_xdt):
    ''' Convert frequency to GHz. Note attrs (channel_width, reference_frequency) still have Hz units in dict '''
    if ms_xdt.frequency.attrs['units'] == "Hz":
        frequency_xda = ms_xdt.frequency / 1e9
        frequency_attrs = ms_xdt.frequency.attrs
        frequency_attrs['units'] = "GHz"
        frequency_xda = frequency_xda.assign_attrs(frequency_attrs)
        ms_xdt.coords['frequency'] = frequency_xda

def _add_baseline_coordinate(ms_xdt):
    '''
        Replace "baseline_id" (int) with "baseline" (string) coordinate "ant1 & ant2".
        Baseline ids are not consistent across ms_xdts. 
    '''
    # Cannot assign coords to DataTree.
    baseline_ms_xdt = ms_xdt.to_dataset() # mutable Dataset

    if 'baseline_id' not in baseline_ms_xdt.coords:
        return baseline_ms_xdt

    ant1_names = ms_xdt.baseline_antenna1_name.values
    ant2_names = ms_xdt.baseline_antenna2_name.values
    if ant1_names.size == 1:
        baseline_names = f"{ant1_names.item()} & {ant2_names.item()}"
        baseline_ms_xdt = baseline_ms_xdt.assign_coords({"baseline": np.array(baseline_names)})
    else:
        baseline_names = [f"{ant1_names[idx]} & {ant2_names[idx]}" for idx in range(len(ant1_names))]
        baseline_ms_xdt = baseline_ms_xdt.assign_coords({"baseline": ("baseline_id", np.array(baseline_names))})
        baseline_ms_xdt = baseline_ms_xdt.swap_dims({"baseline_id": "baseline"})
    baseline_ms_xdt = baseline_ms_xdt.drop("baseline_id")
    return baseline_ms_xdt
