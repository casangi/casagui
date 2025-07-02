''' Apply selection dict to ProcessingSet and MeasurementSetXds '''

import xarray as xr

def select_ps(ps_xdt, logger, query=None, string_exact_match=True, **kwargs):
    '''
        Apply selection query and kwargs to ProcessingSet using exact match or partial match.
        See https://xradio.readthedocs.io/en/latest/measurement_set/schema_and_api/measurement_set_api.html#xradio.measurement_set.ProcessingSetXdt.query
        Select Processing Set first (ps summary columns), then each MeasurementSetXds, where applicable.
        Returns selected ProcessingSet DataTree (may be empty).
    '''
    # Do PSXdt selection
    logger.debug(f"Applying selection to ProcessingSet: query={query}, kwargs={kwargs}")
    try:
        selected_ps_xdt = ps_xdt.xr_ps.query(query=query, string_exact_match=string_exact_match, **kwargs)
    except RuntimeError:
        logger.error("ProcessingSet selection failed")
        return xr.DataTree()

    if kwargs:
        ms_selection = {}
        for key, val in kwargs.items():
            if key in ['polarization', 'scan_name', 'field_name']:
                ms_selection[key] = val
        if ms_selection:
            selected_ps_xdt = select_ms(selected_ps_xdt, logger, **ms_selection)

    selected_ps_xdt.attrs = ps_xdt.attrs
    return selected_ps_xdt

#pylint: disable=too-many-arguments, too-many-positional-arguments
def select_ms(ps_xdt, logger, indexers=None, method=None, tolerance=None, drop=False, **indexers_kwargs):
    ''' Apply selection to each MeasurementSetXdt.
        See https://xradio.readthedocs.io/en/latest/measurement_set/schema_and_api/measurement_set_api.html#xradio.measurement_set.MeasurementSetXdt.sel
        Return selected ProcessingSet DataTree.
    '''
    selected_ps_xdt = xr.DataTree() # return value
    dim_selection = None
    coord_selection = None

    if indexers_kwargs:
        # Sort out selection by dim and coord; xr_ms can only select dim
        logger.debug(f"Applying selection to MeasurementSet: {indexers_kwargs}")
        dim_selection, coord_selection = get_dim_coord_selections(ps_xdt, indexers_kwargs)

    for name, ms_xdt in ps_xdt.items():
        ms = ms_xdt
        include_ms = True

        if coord_selection:
            logger.debug(f"Applying coordinate selection {coord_selection} to MS {name}")
            ms, include_ms = select_coords(ms, logger, coord_selection)

        if include_ms:
            if dim_selection:
                logger.debug(f"Applying dimension selection {dim_selection} to MS {name}")
                try:
                    ms = ms.xr_ms.sel(indexers=indexers, method=method, tolerance=tolerance, drop=drop, **dim_selection)
                except KeyError: # selection failed, go to next MS
                    logger.error(f"MeasurementSet dimension selection failed for ms {name}")
                    continue

            selected_ps_xdt[name] = ms
        else:
            logger.error(f"MeasurementSet coordinate selection failed for ms {name}")
    selected_ps_xdt.attrs = ps_xdt.attrs
    return selected_ps_xdt
#pylint: enable=too-many-arguments, too-many-positional-arguments

def get_dim_coord_selections(ps_xdt, ms_selection):
    ''' Sort selection by dimension and coordinate '''
    data_dims = list(ps_xdt.xr_ps.get_max_dims().keys())
    dim_selection = {}
    coord_selection = {}
    for key, val in ms_selection.items():
        if key in data_dims:
            dim_selection[key] = val
        else:
            coord_selection[key] = val
    return dim_selection, coord_selection

def select_coords(ms, logger, coord_selection):
    ''' Select coordinates which are not dimensions '''
    include_ms = False
    for key, val in coord_selection.items():
        try:
            if 'antenna' in key or 'baseline' in key:
                if key == 'antenna1':
                    ms = ms.sel(baseline_id=ms.baseline_antenna1_name==val, drop=True)
                elif key == 'antenna2':
                    ms = ms.sel(baseline_id=ms.baseline_antenna2_name==val, drop=True)
                elif key == 'baseline':
                    ant1, ant2 = val.split('&')
                    ms = ms.sel(baseline_id=ms.baseline_antenna1_name==ant1.strip(), drop=True)
                    ms = ms.sel(baseline_id=ms.baseline_antenna2_name==ant2.strip(), drop=True)
                if ms.baseline_id.size == 1: # Select baseline_id to remove dimension
                    ms = ms.sel(baseline_id=ms.baseline_id.item())
                elif ms.baseline_id.size == 0:
                    logger.error(f"MeasurementSet {key} selection {val} failed")
                    include_ms = False
                    break
            elif 'field_name' in key:
                ms = ms.sel(time=ms.field_name==val)
            elif 'scan_name' in key:
                ms = ms.sel(time=ms.scan_name==val)
            else:
                raise KeyError(f"Invalid ms selection key {key}")
            include_ms = True
        except KeyError:
            logger.debug(f"MeasurementSet {key} selection {val} failed")
            continue
    return ms, include_ms
