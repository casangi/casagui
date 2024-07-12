'''
Utility functions to manage processing set data
'''
import numpy as np
import xarray as xr

def _set_baseline_coordinates(xds):
    ''' Set baseline, ant1, and ant2 name coordinates.
        Make baseline name a dimension of the xarray Dataset instead of id '''
    ant1 = xds.baseline_antenna1_id.values
    ant2 = xds.baseline_antenna2_id.values
    ant_names = _get_antenna_names(xds.antenna_xds)
    baseline_pairs = []
    ant1_names = []
    ant2_names = []

    for idx in xds.baseline_id.values:
        ant1_name = ant_names[ant1[idx]]
        ant2_name = ant_names[ant2[idx]]
        baseline_pair = f"{ant1_name} & {ant2_name}"
        baseline_pairs.append(baseline_pair)
        ant1_names.append(ant1_name)
        ant2_names.append(ant2_name)

    xds = xds.assign_coords({"baseline": (xds.baseline_id.dims, np.array(baseline_pairs))})
    xds = xds.assign_coords({"Antenna1_name": (xds.baseline_id.dims, np.array(ant1_names))})
    xds = xds.assign_coords({"Antenna2_name": (xds.baseline_id.dims, np.array(ant2_names))})
    return xds.swap_dims({"baseline_id": "baseline"})

def _get_antenna_names(antenna_xds):
    ''' Return lists of antenna names (antenna@station) '''
    names = antenna_xds.name.values
    stations = antenna_xds.station.values
    antennas = [f"{names[i]}@{stations[i]}" for i in range(len(names))]
    return antennas

def set_coordinates(xds):
    ''' Set unit as string (not list) and convert freq to GHz for plotting '''
    for coord in xds.coords:
        if coord == 'baseline_id':
            xds = _set_baseline_coordinates(xds)
        else:
            coord_attrs = xds[coord].attrs
            if 'units' in coord_attrs:
                # reassign unit as string
                unit = coord_attrs['units']
                if isinstance(unit, list):
                    unit = unit[0]
                    coord_attrs['units'] = unit

                if coord == 'frequency' and unit == 'Hz':
                    # reassign frequencies in GHz
                    freq_xda = xds.frequency / 1.0e9
                    coord_attrs['units'] = 'GHz'
                    xds['frequency'] = freq_xda.assign_attrs(coord_attrs)
                else:
                    xds[coord] = xds[coord].assign_attrs(coord_attrs)
    return xds
