''' Apply selection dict to ProcessingSet and MeasurementSetXds '''

def select_ps(ps_xdt, selection, logger):
    '''
        Apply selection dict to Processing Set.
        Select Processing Set first (ps summary columns), then each MeasurementSetXds (data_group etc.).
        Returns dict of selected name, ms_xdt.
        Throws exception for empty Processing Set (null selection).
    '''
    if not selection:
        return ps_xdt

    # Separate PS selection and MS selection
    ps_summary = ps_xdt.xr_ps.summary()
    ps_selection_keys = list(ps_summary.columns.array)
    ps_selection_keys.append('data_group')

    first_ms = ps_summary['name'][0]
    ms_selection_keys = list(ps_xdt[first_ms].coords.keys())

    # Sort selections into categories
    ps_selection = {}
    ms_selection = {}
    antenna_selection = {}
    for key, val in selection.items():
        if key in ps_selection_keys and selection[key]:
            ps_selection[key] = val
        if key in ms_selection_keys and selection[key]:
            ms_selection[key] = val
        if 'antenna1' in key or 'antenna2' in key:
            antenna_selection[key] = val
        elif key == 'baseline':
            ant1, ant2 = val.split('&')
            antenna_selection['antenna1'] = ant1.strip()
            antenna_selection['antenna2'] = ant2.strip()

    # Do PSXdt selection
    logger.debug(f"Applying selection to ProcessingSet: {ps_selection}")

    if ps_selection:
        selected_ps_xdt = ps_xdt.xr_ps.query(**ps_selection)
        if len(selected_ps_xdt) == 0:
            raise RuntimeError("Selection failed: ps selection yielded empty processing set.")
    else:
        selected_ps_xdt = ps_xdt.copy()

    # Do MSXdt selection
    return _select_ms_xdt(selected_ps_xdt, ms_selection, antenna_selection, logger)

def _select_ms_xdt(ps_xdt, ms_selection, antenna_selection, logger):
    ''' Apply selection to each MeasurementSetXds and return ProcessingSet.
        Remove ms_xds which do not contain selection.
    '''
    # Done if no selection to apply
    if not ms_selection and not antenna_selection:
        return ps_xdt

    logger.debug(f"Applying selection to measurement set: {ms_selection}, {antenna_selection}")

    # Drop ms_xdt where selection fails
    names_to_drop = []

    for name, ms_xdt in ps_xdt.items():
        try:
            if antenna_selection:
                for antenna, val in antenna_selection.items():
                    if antenna == 'antenna1':
                        ms_xdt = ms_xdt.sel(baseline_id=ms_xdt.baseline_antenna1_name==val)
                    else:
                        ms_xdt = ms_xdt.sel(baseline_id=ms_xdt.baseline_antenna2_name==val)

                if ms_xdt.baseline_id.size == 1:
                    # Select baseline_id to remove dimension
                    ms_xdt = ms_xdt.sel(baseline_id=ms_xdt.baseline_id.item())
                elif ms_xdt.baseline_id.size == 0:
                    names_to_drop.append(name)
                    continue

            ms_xdt = ms_xdt.xr_ms.sel(**ms_selection)
            ps_xdt[name] = ms_xdt
        except KeyError:
            # selection not in this ms_xdt, do not include in returned ps_xdt
            names_to_drop.append(name)

    if names_to_drop:
        ps_xdt = ps_xdt.drop_nodes(names_to_drop)

    if len(ps_xdt) == 0:
        raise RuntimeError("Selection failed: ms selection yielded empty processing set.")

    return ps_xdt
