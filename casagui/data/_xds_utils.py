'''
Utility functions to manage processing set data
'''
import numpy as np
import xarray as xr

def set_name_dims(xds):
    ''' Set baseline, ant1, and ant2 name coordinates.
        Make baseline name a dimension of the xarray Dataset instead of id '''
    ant1 = xds.baseline_antenna1_id.values
    ant2 = xds.baseline_antenna2_id.values
    ant_names = _get_antenna_names(xds.antenna_xds)
    baseline_names = []
    ant1_names = []
    ant2_names = []

    for idx in xds.baseline_id.values:
        ant1_name = ant_names[ant1[idx]]
        ant2_name = ant_names[ant2[idx]]
        baseline_name = f"{ant1_name} & {ant2_name}"
        baseline_names.append(baseline_name)
        ant1_names.append(ant1_name)
        ant2_names.append(ant2_name)

    xds = xds.assign_coords({"baseline": (xds.baseline_id.dims, np.array(baseline_names))})
    xds = xds.assign_coords({"Antenna1_name": (xds.baseline_id.dims, np.array(ant1_names))})
    xds = xds.assign_coords({"Antenna2_name": (xds.baseline_id.dims, np.array(ant2_names))})
    xds = xds.swap_dims({'baseline_id': 'baseline'})
    return xds

def _get_antenna_names(antenna_xds):
    ''' Return lists of antenna names (antenna@station) '''
    names = antenna_xds.name.values
    stations = antenna_xds.station.values
    antennas = [f"{names[i]}@{stations[i]}" for i in range(len(names))]
    return antennas

def fix_coordinate_units(xds):
    ''' Set unit as string (not list) and convert freq to GHz if Hz '''
    for coord in xds.coords:
        if 'units' in xds[coord].attrs:
            # unit as string
            unit = xds[coord].attrs['units']
            if isinstance(unit, list):
                unit = unit[0]

            if coord == 'frequency' and unit == 'Hz':
                xds['frequency'] = xds.frequency / 1.0e9
                xds['frequency'] = xds.frequency.assign_attrs(units='GHz')
            else:
                xds[coord] = xds[coord].assign_attrs(units=unit)
