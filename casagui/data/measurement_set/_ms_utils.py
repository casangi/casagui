'''
Utility functions to manage xarray DataSets
'''

import numpy as np
import xarray as xr


def set_baseline_coordinate(ps, drop_ant_names):
    ''' Set baseline coordinate as string array (ant1_name & ant2_name).
        Replace baseline_id dimension with new baseline coordinate.
        If drop_ant_names, remove antenna name coordinates. '''
    for name, xds in ps.items():
        if 'baseline_id' not in xds.coords:
            break

        ant1_names = xds.baseline_antenna1_name.values
        ant2_names = xds.baseline_antenna2_name.values
        baseline_names = []

        # Create baseline name coordinate and make it dimension
        for idx in xds.baseline_id.values:
            baseline_name = f"{ant1_names[idx]} & {ant2_names[idx]}"
            baseline_names.append(baseline_name)
        xds = xds.assign_coords({"baseline": (xds.baseline_id.dims, np.array(baseline_names))})
        xds = xds.swap_dims({"baseline_id": "baseline"})

        if drop_ant_names:
            # Remove non-dimension unicode data_vars for concat (raster plot).
            # Antenna names now in baseline coord "ant1 & ant2".
            xds = xds.drop("baseline_antenna1_name")
            xds = xds.drop("baseline_antenna2_name")

        ps[name] = xds

def concat_ps_xds(ps, logger):
    ''' Concatenate xarray Datasets in processing set by given dimension.
        Return concat xds. '''
    ps_len = len(ps)
    if ps_len == 0:
        raise RuntimeError("Processing set empty after selection.")

    if ps_len == 1:
        logger.debug("Processing set contains one dataset, nothing to concat.")
        return ps.get(0)

    ms_xds_list = []
    first_time_values = []

    # xds have time ranges from different scans, so split xds at time gaps
    sorted_time_values = _get_sorted_times(ps)
    for key in ps:
        split_ms_xds, first_xds_times = _split_xds_by_time_gap(ps[key], sorted_time_values)
        ms_xds_list.extend(split_ms_xds)
        first_time_values.extend(first_xds_times)

    if len(ms_xds_list) < ps_len:
        logger.debug(f"Split {ps_len} datasets by time gap into {ms_xds_list_len} datasets.")

    # Create sorted xds list using sorted first values
    sorted_xds = [None] * len(ms_xds_list)
    first_time_values.sort()
    for ms_xds in ms_xds_list:
        first_xds_time = ms_xds['time'].values
        if first_xds_time.size > 1:
            first_xds_time = first_xds_time[0]

        # Assign first unused xds at index with same first value
        for idx, value in enumerate(first_time_values):
            if (value == first_xds_time) and (sorted_xds[idx] is None):
                # Convert MeasurementSetXds to xarray Dataset for concat
                sorted_xds[idx] = xr.Dataset(ms_xds.data_vars, ms_xds.coords, ms_xds.attrs)
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
