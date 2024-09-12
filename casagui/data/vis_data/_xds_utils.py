'''
Utility functions to manage xarray DataSets
'''

import numpy as np
import xarray as xr

def _set_baseline_coordinates(xds):
    ''' Set baseline, ant1, and ant2 name coordinates.
        Make baseline name a dimension of the xarray Dataset instead of id '''
    ant1_names = xds.baseline_antenna1_name.values
    ant2_names = xds.baseline_antenna2_name.values
    baseline_names = []

    for idx in xds.baseline_id.values:
        baseline_name = f"{ant1_names[idx]} & {ant2_names[idx]}"
        baseline_names.append(baseline_name)

    # Add baseline name coordinate and make it dimension
    xds = xds.assign_coords({"baseline": (xds.baseline_id.dims, np.array(baseline_names))})
    xds = xds.swap_dims({"baseline_id": "baseline"})

    # Raises error in concat when non-dim data var is string type ("dtype.hasobject not implemented for auto chunking")
    # Drop antenna name coordinates: no longer needed since baseline names assigned as dim below
    xds = xds.drop('baseline_antenna1_name')
    xds = xds.drop('baseline_antenna2_name')

    return xds

def set_coordinates(xds):
    ''' Set unit as string (not list) and convert freq to GHz for plotting '''
    for coord in xds.coords:
        if coord == 'baseline_id':
            xds = _set_baseline_coordinates(xds)
        elif coord in xds.coords: # not removed
            coord_attrs = xds[coord].attrs
            if 'units' in coord_attrs:
                # reassign unit as string
                unit = coord_attrs['units']
                if isinstance(unit, list) and len(unit) == 1:
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

def concat_ps_xds(ps, logger):
    ''' Concatenate xarray Datasets in processing set by given dimension.
        Return concat xds. '''
    n_xds = len(ps)
    if n_xds == 0:
        raise RuntimeError("Processing set empty after selection.")

    if n_xds == 1:
        logger.debug("Processing set contains one dataset, nothing to concat.")
        return ps.get(0)

    xds_list = []
    first_values = []

    # xds have time ranges from different scans, so split xds at time gaps
    sorted_time_values = _get_sorted_times(ps)
    for key in ps:
        split_xds, first_xds_times = _split_xds_by_time_gap(ps[key], sorted_time_values)
        xds_list.extend(split_xds)
        first_values.extend(first_xds_times)
    if len(xds_list) < n_xds:
        logger.debug(f"Split {n_xds} datasets by time gap into {len(xds_list)} datasets.")

    # Create sorted xds list using sorted first values
    sorted_xds = [None] * len(xds_list)
    first_values.sort()
    for xds in xds_list:
        first_xds_value = xds['time'].values
        if first_xds_value.size > 1:
            first_xds_value = first_xds_value[0]

        # Assign first unused xds at index with same first value
        for idx, value in enumerate(first_values):
            if (value == first_xds_value) and (sorted_xds[idx] is None):
                sorted_xds[idx] = xds
                break

    return xr.concat(sorted_xds, dim='time')

def _get_sorted_times(ps):
    values = []
    for key in ps:
        time_values = ps[key].time.values
        if time_values.size > 1:
            values.extend(time_values.tolist())
        else:
            values.append(time_values)
    return sorted(values)

def _split_xds_by_time_gap(xds, sorted_times):
    ''' Split xds where there is a gap in sorted times.
        Return list of xds and first time in each one. '''
    times = xds.time.values.ravel()
    xds_list = []
    first_times = [times[0]]

    if len(times) == 1:
        xds_list.append(xds)
    else:
        sorted_time_idx = sorted_times.index(times[0])
        xds_start_idx = 0 # start for iselection

        for idx, time in enumerate(times):
            if time == sorted_times[sorted_time_idx]:
                # No time gap
                sorted_time_idx += 1
                continue

            # Found time gap, select xds
            xds_list.append(xds.isel(time=slice(xds_start_idx, idx)))

            # start next xds
            first_times.append(times[idx])
            sorted_time_idx = sorted_times.index(time) + 1 # for next time
            xds_start_idx = idx

        # add last time range xds
        xds_list.append(xds.isel(time=slice(xds_start_idx, idx + 1)))

    return xds_list, first_times
