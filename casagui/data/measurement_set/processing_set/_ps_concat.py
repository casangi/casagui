'''
Concat ProcessingSet xarray DataSets into single xds by time dimension (in order)
'''

import xarray as xr

from casagui.data.measurement_set.processing_set._ps_coords import set_coordinates

def concat_ps_xdt(ps_xdt, logger):
    ''' Concatenate xarray Datasets in ProcessingSet by time dimension.
        Return concat xds. '''
    if len(ps_xdt) == 0:
        raise RuntimeError("Processing set empty after selection.")

    ps = {}
    for name, ms_xdt in ps_xdt.items():
        # Set units to str not list and set baseline coordinate.  Returns xarray.Dataset
        ps[name] = set_coordinates(ms_xdt)

    if len(ps) == 1:
        logger.debug("Processing set contains one dataset, nothing to concat.")
        return list(ps.values())[0]

    # Split xds by time gaps
    sorted_times = _get_sorted_times(ps)
    xds_list = []
    time_list = []
    for xds in ps.values():
        xdss, times = _split_xds_by_time_gap(xds, sorted_times)
        xds_list.extend(xdss)
        time_list.extend(times)

    if len(xds_list) > len(ps_xdt):
        logger.debug(f"Split {len(ps_xdt)} datasets by time gap into {len(xds_list)} datasets.")

    # Create sorted xds list using sorted times
    time_list.sort()
    sorted_xds = [None] * len(time_list)

    for xds in xds_list:
        try:
            first_xds_time = xds.time.values[0]
        except IndexError: # only one value
            first_xds_time = xds.time.values

        for idx, value in enumerate(time_list):
            if value == first_xds_time and sorted_xds[idx] is None:
                if "baseline" in xds.coords:
                    # Cannot concat with non-dim string coord
                    xds = xds.drop("baseline_antenna1_name")
                    xds = xds.drop("baseline_antenna2_name")
                # Convert MeasurementSetXds to xr Dataset for concat
                # (TypeError: MeasurementSetXds.__init__() got an unexpected keyword argument 'coords')
                sorted_xds[idx] = xr.Dataset(xds.data_vars, xds.coords, xds.attrs)
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
        idx = xds_start_idx = 0 # start for iselection

        for idx, time in enumerate(times):
            if time == sorted_times[sorted_time_idx]:
                # No time gap, go to next time
                sorted_time_idx += 1
                continue

            # Found time gap, select xds
            xds_list.append(xds.isel(time=slice(xds_start_idx, idx)))

            # start next xds with new first time, find idx in sorted times (skip ahead)
            xds_start_idx = idx
            first_times.append(times[idx])
            sorted_time_idx = sorted_times.index(time) + 1 # for next time

        # add last time range xds
        xds_list.append(xds.isel(time=slice(xds_start_idx, idx + 1)))

    return xds_list, first_times
