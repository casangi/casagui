'''
Modify/add xarray Dataset coordinates for plotting.
'''

import numpy as np
from pandas import to_datetime

def set_coordinates(xds):
    _set_coordinate_unit(xds)
    return _set_baseline_coordinate(xds)

def set_datetime_coordinate(xds):
    ''' Convert float time to datetime for plotting. '''
    time_attrs = xds.time.attrs
    try:
        xds['time'] = to_datetime(xds.time, unit=time_attrs['units'], origin=time_attrs['format'])
    except TypeError:
        xds['time'] = to_datetime(xds.time, unit=time_attrs['units'][0], origin=time_attrs['format'])
    xds.time.attrs = time_attrs

def set_index_coordinates(xds, coordinates):
    ''' Replace string coordinate values with numerical index for x and y axis '''
    for coordinate in coordinates:
        if coordinate == "polarization":
            xds["polarization"] = np.array(range(xds.polarization.size))
        elif coordinate == "baseline":
            xds["baseline"] = np.array(range(xds.baseline.size))
        elif coordinate == "antenna_name":
            all_ant_names = xds.antenna_xds.antenna_name.values.tolist()
            xds_ant_ids = [all_ant_names.index(ant_name) for ant_name in xds.antenna_name.values]
            xds["antenna_name"] = np.array(xds_ant_ids)

def _set_coordinate_unit(xds):
    ''' Set coordinate units attribute as string not list for plotting. '''
    for coord in xds.coords:
        # Plots need unit to be string not list
        if 'units' in xds[coord].attrs:
            units = xds[coord].units
            if isinstance(units, list) and len(units) == 1:
                xds[coord].attrs['units'] = units[0]

def _set_baseline_coordinate(xds):
    '''
        Replace "baseline_id" with "baseline" string coordinate "ant1 & ant2".
        Baseline ids are not consistent across ms xds.
    '''
    if 'baseline_id' in xds.coords:
        ant1_names = xds.baseline_antenna1_name.values
        ant2_names = xds.baseline_antenna2_name.values
        baseline_ids = xds.baseline_id.values
        baseline_names = [f"{ant1_names[idx]} & {ant2_names[idx]}" for idx in baseline_ids]
        xds = xds.assign_coords({"baseline": (xds.baseline_id.dims, np.array(baseline_names))})
        xds = xds.swap_dims({"baseline_id": "baseline"})
        xds = xds.drop("baseline_id")
    return xds
