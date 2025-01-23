'''
Concat ProcessingSet xarray DataSets into single xds by time dimension (in order)
'''

import numpy as np
import xarray as xr

def concat_ps_xds(ps, logger):
    ''' Concatenate xarray Datasets in ProcessingSet by time dimension.
        Return concat xds. '''
    ps_len = len(ps)
    if ps_len == 0:
        raise RuntimeError("Processing set empty after selection.")

    if ps_len == 1:
        logger.debug("Processing set contains one dataset, nothing to concat.")
        return ps.get(0)

    # Split xds by scan numbers
    xds_list = []
    scan_list = []
    for xds in ps.values():
        scans, xdss = _split_xds_by_scan(xds)
        scan_list.extend(scans)
        xds_list.extend(xdss)

    # Create sorted xds list using sorted scan numbers
    scan_list.sort()
    sorted_xds = [None] * len(scan_list)

    for xds in xds_list:
        try:
            first_scan = xds.scan_number.values[0]
        except IndexError: # only one value
            first_scan = xds.scan_number.values

        for idx, value in enumerate(scan_list):
            if value == first_scan and sorted_xds[idx] is None:
                if "baseline" in xds.coords:
                    # Cannot concat with non-dim string coord
                    xds = xds.drop("baseline_antenna1_name")
                    xds = xds.drop("baseline_antenna2_name")
                # Convert MeasurementSetXds to xr Dataset for concat
                # (TypeError: MeasurementSetXds.__init__() got an unexpected keyword argument 'coords')
                sorted_xds[idx] = xr.Dataset(xds.data_vars, xds.coords, xds.attrs)
                break
    return xr.concat(sorted_xds, dim='time')

def _split_xds_by_scan(xds):
    ''' Split xds according to scan number.
        Return list of xds and scan number for each. '''
    scan_list = []
    xds_list = []
    for scan in sorted(set(xds.scan_number.values)):
        scan_list.append(scan)
        xds_list.append(xds.sel(time=xds.scan_number==scan))
    return scan_list, xds_list
