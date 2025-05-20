''' Apply selection dict to ProcessingSet and MeasurementSetXds '''

from xradio.measurement_set.processing_set import ProcessingSet

def select_ps(ps, selection, logger):
    '''
        Apply selection dict to Processing Set.
        Select Processing Set first (ps summary columns), then each MeasurementSetXds (data_group etc.).
        Returns selected Processing Set.
        Throws exception for empty Processing Set (null selection).
    '''
    if not selection:
        return ps

    ps_selection_keys = list(ps.summary().columns.array)
    ps_selection_keys.append('query')
    ms_selection_keys = list(ps.get(0).coords.keys())
    ms_selection_keys.append('data_group')

    ps_selection = {}
    ms_selection = {}

    for key in selection:
        if key in ps_selection_keys and selection[key]:
            ps_selection[key] = selection[key]
        if key in ms_selection_keys and selection[key]:
            ms_selection[key] = selection[key]

    # Do ProcessingSet selection
    if ps_selection:
        selected_ps = ps.sel(**ps_selection)
        if len(selected_ps) == 0:
            raise RuntimeError("Selection failed: ps selection yielded empty processing set.")
    else:
        selected_ps = ps

    # Do MSXds selection
    selected_ps = _select_ms_xds(selected_ps, ms_selection, logger)
    if len(selected_ps) == 0:
        raise RuntimeError("Selection failed: ms selection yielded empty processing set.")

    return selected_ps

def _select_ms_xds(ps, ms_selection, logger):
    ''' Apply selection to each MeasurementSetXds and return ProcessingSet.
        Remove ms_xds which do not contain selection.
    '''
    # Done if no MS selection
    if not ms_selection:
        return ps

    logger.debug(f"Applying selection to measurement set xds: {ms_selection}")

    antenna_selection = {}
    for key in ms_selection:
        if 'antenna' in key:
            antenna_selection[key] = ms_selection[key]
    for key in antenna_selection:
        ms_selection.pop(key)

    selected_ps = ProcessingSet()

    if ms_selection:
        data_group = ms_selection.pop('data_group') if 'data_group' in ms_selection else None

        for name, ms_xds in ps.items():
            # Apply data_group selection
            if data_group:
                selected_xds = ms_xds.sel(data_group_name=data_group)
            else:
                selected_xds = ms_xds
            # Apply MS selection
            if ms_selection:
                try:
                    selected_ps[name] = selected_xds.sel(**ms_selection)
                except KeyError:
                    pass # selection not in this xds, do not include in returned ps
            else:
                selected_ps[name] = selected_xds

    # Do antenna selection
    return _select_antenna(selected_ps, antenna_selection)

def _select_antenna(ps, antenna_selection):
    ''' Select baselines by antenna coordinate '''
    # Done if no antenna selection
    if not antenna_selection:
        return ps

    selected_ps = ProcessingSet()

    for name, ms_xds in ps.items():
        for key, value in antenna_selection.items():
            try:
                if key == 'antenna1':
                    selected_ps[name] = ms_xds.sel(baseline=ms_xds.baseline_antenna1_name==value)
                elif key == 'antenna2':
                    selected_ps[name] = ms_xds.sel(baseline=ms_xds.baseline_antenna2_name==value)
            except KeyError:
                pass # selection not in this xds, do not include in returned ps

    return selected_ps
