''' Apply selection dict to ProcessingSet and MeasurementSetXds '''

import xarray as xr

def select_ps(ps_xdt, logger, query=None, string_exact_match=False, **kwargs):
    '''
        Apply selection query and kwargs to ProcessingSet using exact match or partial match.
        See https://xradio.readthedocs.io/en/latest/measurement_set/schema_and_api/measurement_set_api.html#xradio.measurement_set.ProcessingSetXdt.query
        Select Processing Set first (ps summary columns), then each MeasurementSetXds, where applicable.
        Returns selected ProcessingSet DataTree (None if null selection).
    '''
    # Do PSXdt selection
    logger.debug(f"Applying selection to ProcessingSet: query={query}, kwargs={kwargs}")

    try:
        selected_ps_xdt = ps_xdt.xr_ps.query(query=query, string_exact_match=string_exact_match, **kwargs)
        # TODO: select ms
        return selected_ps_xdt
    except RuntimeError as e:
        return None

def select_ms(ps_xdt, logger, indexers=None, method=None, tolerance=None, drop=False, **indexers_kwargs):
    ''' Apply selection to each MeasurementSetXdt.
        See https://xradio.readthedocs.io/en/latest/measurement_set/schema_and_api/measurement_set_api.html#xradio.measurement_set.MeasurementSetXdt.sel
        Return selected ProcessingSet DataTree.
    '''
    logger.debug(f"Applying selection to MeasurementSet: {indexers_kwargs}")

    # Sort out selection by dim and coord; xr_ms can only select dim
    data_dims = list(ps_xdt.xr_ps.get_max_dims().keys())
    dim_selection = {}
    coord_selection = {}
    for key, val in indexers_kwargs.items():
        if key in data_dims:
            dim_selection[key] = val
        else:
            coord_selection[key] = val

    selected_ps_xdt = xr.DataTree() # return value

    for name, ms_xdt in ps_xdt.items():
        ms = ms_xdt
        include_ms = True

        if coord_selection:
            for key, val in coord_selection.items():
                if 'antenna' in key or 'baseline' in key:
                    if key == 'antenna1':
                        ms = ms.sel(baseline_id=ms.baseline_antenna1_name==val, drop=True)
                    elif key == 'antenna2':
                        ms = ms.sel(baseline_id=ms.baseline_antenna2_name==val, drop=True)
                    elif key == 'baseline':
                        ant1, ant2 = val.split('&')
                        try:
                            ms = ms.sel(baseline_id=ms.baseline_antenna1_name==ant1.strip(), drop=True)
                            ms = ms.sel(baseline_id=ms.baseline_antenna2_name==ant2.strip(), drop=True)
                        except KeyError:
                            include_ms = False
                            break
                    if ms.baseline_id.size == 1: # Select baseline_id to remove dimension
                        ms = ms.sel(baseline_id=ms.baseline_id.item())
                    elif ms.baseline_id.size == 0:
                        include_ms = False
                        break
                elif 'field_name' in key:
                    ms = ms.sel(time=ms.field_name==val)
                elif 'scan_name' in key:
                    ms = ms.sel(time=ms.scan_name==val)

        if include_ms:
            if dim_selection:
                try:
                    ms = ms.xr_ms.sel(indexers=indexers, method=method, tolerance=tolerance, drop=drop, **dim_selection)
                except KeyError: # selection failed
                    continue
            selected_ps_xdt[name] = ms

    return selected_ps_xdt
