''' Apply selection dict to ProcessingSet or MeasurementSetXds '''

from xradio.measurement_set.processing_set import ProcessingSet

def select_ps(ps, selection, logger, data_dims, data_group=None):
    '''
        Apply selection dict and optional data group to processing set.
        Select ProcessingSet first, then each MeasurementSetXds.
        Returns selected ProcessingSet.
        Throws exception for empty ProcessingSet (null selection).
    '''
    if not selection and not data_group:
        return ps

    ms_selection = {}
    ps_selection = {}

    if selection:
        ps_selection_keys = list(ps.summary().columns.array)
        ps_selection_keys.append('query')

        for key in selection:
            if key in ps_selection_keys:
                ps_selection[key] = selection[key]
            if key in data_dims:
                ms_selection[key] = selection[key]

    # Do ProcessingSet selection
    if ps_selection:
        logger.info(f"Applying selection to processing set: {ps_selection}")
        selected_ps = ps.sel(**ps_selection)
        if len(selected_ps) == 0:
            raise RuntimeError("Selection failed: ps selection yielded empty processing set.")
    else:
        selected_ps = ps

    # ProcessingSet selection only?
    if not ms_selection and not data_group:
        return selected_ps

    # Do MeasurementSetXds selection
    if ms_selection:
        logger.info(f"Applying selection to measurement set xds: {ms_selection}")

    selected_ms_ps = ProcessingSet()
    for name, ms_xds in selected_ps.items():
        if data_group:
            selected_ms_xds = ms_xds.sel(data_group_name=data_group)
        else:
            selected_ms_xds = ms_xds

        if ms_selection:
            try:
                selected_ms_xds = selected_ms_xds.sel(**ms_selection)
                selected_ms_ps[name] = selected_ms_xds
            except KeyError: # selection not in this xds, do not include in returned ps
                pass
        else:
            selected_ms_ps[name] = selected_ms_xds

    if len(selected_ms_ps) == 0:
        raise RuntimeError("Selection failed: ms selection yielded empty processing set.")

    return selected_ms_ps
