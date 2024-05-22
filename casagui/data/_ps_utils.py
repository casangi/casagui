'''
Utility functions to manage processing set data
'''
import numpy as np
import xarray as xr

from xradio.vis._processing_set import processing_set

def apply_ps_selection(ps, selection, select_ddi):
    ''' Return processing set with ddi, intent, and field selection applied.
        Raise exception if selection is invalid. '''
    if not selection:
        selection = {}
    ddi_sel = selection['ddi'] if 'ddi' in selection.keys() else None
    field_sel = selection['field'] if 'field' in selection.keys() else None
    intent_sel = selection['intent'] if 'intent' in selection.keys() else None

    # Apply input selections
    selected_ps = {}
    if ddi_sel or field_sel or intent_sel:
        for key in ps:
            xds = ps[key]

            # Check ddi selection
            if ddi_sel is not None:
                if (isinstance(ddi_sel, int) and xds.ddi == ddi_sel) or \
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

    # If selecting ddi, select first ddi after field/intent selection applied
    if ddi_sel is None and select_ddi:
        if not selected_ps:
            selected_ps = ps
        ps_ddis = sorted(set(selected_ps.summary()['ddi']))
        ddi_sel = ps_ddis[0]
        selection['ddi'] = ps_ddis[0]

        ddi_ps = {}
        for key in selected_ps:
            xds = selected_ps[key]
            # Check ddi selection
            if (isinstance(ddi_sel, int) and xds.ddi != ddi_sel) or \
                (isinstance(ddi_sel, list) and xds.ddi not in ddi_sel):
                continue # not xds for selected ddi
            ddi_ps[key] = xds

        selected_ps = ddi_ps

    print(f"Processing set selection: {{ddi: {ddi_sel}, field: {field_sel}, intent: {intent_sel}}}")

    if len(selected_ps) == 0:
        raise ValueError(f"Null selection: processing set is empty.")

    # Return selection with ddi
    return processing_set(selected_ps), selection

def concat_ps_xds(ps):
    ''' Concatenate xarray Datasets in processing set '''
    xds_list = [ps[key] for key in ps]

    if len(xds_list) == 0:
        raise RuntimeError("Metadata selection resulted in no datasets.")

    print("Plotting", len(xds_list), "msv4 datasets.")
    return xr.concat(xds_list, dim='time')
