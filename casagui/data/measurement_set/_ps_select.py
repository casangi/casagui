''' Apply selection dict to ProcessingSet or MeasurementSetXds '''

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

    ps_selection = {}
    ms_selection = {}
    antenna_selection = {}

    if selection:
        ps_selection_keys = list(ps.summary().columns.array)
        ps_selection_keys.append('query')

        ms_selection_keys = []
        ms_selection_keys.extend(ps.get(0).coords.keys())

        for key in selection:
            if key in ps_selection_keys:
                ps_selection[key] = selection[key]
                if key in ms_selection_keys:
                    # ps selection selects ms_xdss which _contain_ value but also need to _select_ value
                    ms_selection[key] = selection[key]
            elif "antenna" in key:
                antenna_selection[key] = selection[key]
            else: # assume in ms_xds
                ms_selection[key] = selection[key]

    # Do ProcessingSet selection
    if ps_selection:
        logger.debug(f"Applying selection to processing set: {ps_selection}")
        selected_ps = ps.sel(**ps_selection)
        if len(selected_ps) == 0:
            raise RuntimeError("Selection failed: ps selection yielded empty processing set.")
    else:
        selected_ps = ps

    # Done if ProcessingSet selection only
    if not ms_selection:
        return selected_ps

    # Do MeasurementSetXds selection
    if ms_selection or antenna_selection:
        logger.debug(f"Applying selection to measurement set xds: {ms_selection | antenna_selection}")

    data_group = None
    if ms_selection and 'data_group' in ms_selection:
        data_group = ms_selection.pop('data_group')

    selected_ms_ps = ProcessingSet()
    for name, ms_xds in selected_ps.items():
        if data_group:
            selected_xds = ms_xds.sel(data_group_name=data_group)
        else:
            selected_xds = ms_xds

        if ms_selection or antenna_selection:
            try:
                selected_xds = selected_xds.sel(**ms_selection)
            except KeyError as ke:
                pass # selection not in this xds, do not include in returned ps

            for key, value in antenna_selection.items():
                if key == 'antenna1':
                    selected_xds = selected_xds.sel(baseline=selected_xds.baseline_antenna1_name==value)
                elif key == 'antenna2':
                    selected_xds = selected_xds.sel(baseline=selected_xds.baseline_antenna2_name==value)

            selected_ms_ps[name] = selected_xds
        else:
            selected_ms_ps[name] = selected_xds

    if len(selected_ms_ps) == 0:
        raise RuntimeError("Selection failed: ms selection yielded empty processing set.")

    return selected_ms_ps
