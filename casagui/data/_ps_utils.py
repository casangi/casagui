'''
Utility functions to manage processing set data
'''
from math import isclose

import dask
import numpy as np
from pandas import to_datetime
import xarray as xr

from xradio.vis._processing_set import processing_set

def apply_ps_selection(ps, selection, logger):
    ''' Return processing set with ddi, field, intent selection applied.
        Raise exception if selection is invalid.
        Returns selected ps.
    '''
    if not selection:
        return ps

    ddi_sel = selection['ddi'] if 'ddi' in selection.keys() else None
    field_sel = selection['field'] if 'field' in selection.keys() else None
    intent_sel = selection['intent'] if 'intent' in selection.keys() else None

    # Return if no ps selection
    if ddi_sel == None and field_sel == None and intent_sel == None:
        return ps

    logger.info(f"Processing set selection: {{ddi: {ddi_sel}, field: {field_sel}, intent: {intent_sel}}}")

    selected_ps = {}
    for key in ps:
        xds = ps[key]

        # Check ddi selection
        if ddi_sel is not None:
            if (isinstance(ddi_sel, int) and xds.ddi != ddi_sel) or \
                (isinstance(ddi_sel, list) and xds.ddi not in ddi_sel):
                continue # not xds for selected ddi

        # Check field selection
        if field_sel is not None:
            field_info = xds.VISIBILITY.field_info
            if (isinstance(field_sel, int) and field_info['field_id'] != field_sel) or \
                (isinstance(field_sel, str) and field_info['name'] != field_sel) or \
                (isinstance(field_sel, list) and (field_info['name'] not in field_sel or \
                field_info['field_id'] not in field_sel)):
                continue # not xds for selected field

        # Check intent selection
        if intent_sel is not None:
            if (isinstance(intent_sel, str) and xds.intent != intent_sel) or \
                (isinstance(intent_sel, list) and xds.intent not in intent_sel):
                continue # not xds for selected intent

        # Passed all selection checks
        selected_ps[key] = xds

    if len(selected_ps) == 0:
        raise ValueError(f"Null selection: processing set is empty.")

    return processing_set(selected_ps)

def concat_ps_xds(ps, logger):
    ''' Concatenate xarray Datasets in processing set by time order '''
    n_xds = len(ps)
    if n_xds == 0:
        raise RuntimeError("No processing set datasets after selection.")

    if n_xds == 1:
        return ps.get(0)
    else:
        # xds have overlapping time ranges
        # Split xds where there are time gaps
        xds_list = []
        first_times_list = []
        for key in ps:
            split_time_xds, first_times = _split_xds_times(ps[key])
            xds_list.extend(split_time_xds)
            first_times_list.extend(first_times)
        logger.debug(f"Split {n_xds} datasets by scan into {len(xds_list)} datasets.")

        # Create sorted xds list using sorted first times
        sorted_xds = [None] * len(xds_list)
        first_times_list.sort()
        for xds in xds_list:
            list_idx = first_times_list.index(xds.time.values[0])
            sorted_xds[list_idx] = xds

        return xr.concat(sorted_xds, dim='time')

def _split_xds_times(xds):
    ''' Split xds where there is a time gap. Return xds list and first times '''
    interval = xds.time.attrs['integration_time']['data']
    times = xds.time.values.ravel()

    time_xds = []
    first_times = []
    start_idx = 0

    for idx, time in enumerate(times):
        gap = time - times[idx - 1] if idx > 0 else interval
        # can have gap from dropped timestamps; need 30 sec gap for slew
        if gap > interval and gap > 30.0:
            first_times.append(times[start_idx])
            time_xds.append(xds.isel(time=slice(start_idx, idx)))
            start_idx = idx

    # add last time chunk
    first_times.append(times[start_idx])
    time_xds.append(xds.isel(time=slice(start_idx, idx + 1)))

    return time_xds, first_times
