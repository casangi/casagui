'''
Class using xradio Processing Set for accessing and selecting MeasurementSet data.
'''

try:
    import pandas as pd
    from xradio.measurement_set.processing_set import ProcessingSet
    _have_xradio = True
    from casagui.data.measurement_set._ps_coords import set_coordinates
    from casagui.data.measurement_set._ps_select import select_ps
    from casagui.data.measurement_set._ps_stats import calculate_ps_stats
    from casagui.data.measurement_set._raster_data import raster_data
    from casagui.data.measurement_set._xds_data import get_correlated_data, get_dimension_values
    from casagui.io._ms_io import get_processing_set
except ImportError as e:
    _have_xradio = False


class PsData:

    def __init__(self, ms, logger):
        if not _have_xradio:
            raise RuntimeError("xradio package not available for reading MeasurementSet")
        if not ms:
            raise RuntimeError("MS path not available for reading MeasurementSet")

        self._ps, self._zarr_path = get_processing_set(ms, logger)
        self._logger = logger

        # Convert units, create "baseline" coordinate from "baseline_id" and antenna names
        for name, xds in self._ps.items():
            self._ps[name] = set_coordinates(xds)

        self._selection = {}
        self._selected_ps = None # cumulative selection
        self._iter_selected_ps = None # not cumulative selection

    def get_path(self):
        return self._zarr_path

    def summary(self, columns=None):
        pd.set_option("display.max_rows", len(self._ps))
        pd.set_option("display.max_columns", 12)
        ps_summary = self._ps.summary()

        if columns is None:
            print(ps_summary)
        elif columns == "by_msv4":
            for row in ps_summary.itertuples(index=False):
                name, intents, shape, polarization, scan_number, spw_name, field_name, source_name, line_name, field_coords, start_frequency, end_frequency = row
                print("-----")
                print(f"MSv4 name: {name}")
                print(f"intent: {intents}")
                print(f"shape: {shape[0]} times, {shape[1]} baselines, {shape[2]} channels, {shape[3]} polarizations")
                print(f"polarization: {polarization}")
                print(f"scan_number: {scan_number}")
                print(f"spw_name: {spw_name}")
                print(f"field_name: {field_name}")
                print(f"source_name: {source_name}")
                print(f"line_name: {line_name}")
                print(f"field_coords: ({field_coords[0]}) {field_coords[1]} {field_coords[2]}")
                print(f"frequency range: {start_frequency:e} - {end_frequency:e}")
            print("-----")
        else:
            if isinstance(columns, str):
                columns = [columns]
            col_df = ps_summary[columns]
            print(col_df)
            if len(columns) == 1:
                return self._get_unique_values(col_df)

    def get_data_groups(self):
        data_groups = []
        for xds_name in self._ps:
            data_groups.extend(list(self._ps[xds_name].data_groups))
        return set(data_groups)

    def get_antennas(self, plot_positions=False):
        if plot_positions:
            self._ps.plot_antenna_positions()
        return self._ps.get_combined_antenna_xds().antenna_name.values.tolist()

    def plot_phase_centers(self, label_all_fields=False, data_group='base'):
        self._ps.plot_phase_centers(label_all_fields, data_group)

    def get_ps_len(self):
        return len(self._get_ps())

    def get_ps_max_dims(self):
        ps = self._get_ps()
        return ps.get_ps_max_dims()

    def get_data_dimensions(self):
        ''' Return list of data dimension names in Processing Set. '''
        max_dims = self.get_ps_max_dims()
        dims = list(max_dims.keys())
        if 'uvw_label' in dims:
            dims.remove('uvw_label')
        return dims

    def get_dimension_values(self, dim):
        ''' Return list of values for dimension in ProcessingSet data group. '''
        ps = self._get_ps()
        return get_dimension_values(ps, dim)

    def get_first_spw(self):
        ''' Return first spw name by id '''
        spw_id_names = {}
        ps = self._get_ps()
        for xds in ps.values():
            freq_xds = xds.frequency
            spw_id_names[freq_xds.spectral_window_id] = freq_xds.spectral_window_name

        first_spw_id = min(spw_id_names)
        first_spw_name = spw_id_names[first_spw_id]

        spw_df = ps.summary()[ps.summary()['spw_name'] == first_spw_name]
        self._logger.info(f"Selecting first spw {first_spw_name} (id {first_spw_id}) with frequency range {spw_df.at[spw_df.index[0], 'start_frequency']:e} - {spw_df.at[spw_df.index[0], 'end_frequency']:e}")
        return first_spw_name

    def select_data(self, selection):
        ''' Apply selection dict to ProcessingSet to create selected ps.
            If previous selection done, apply to selected ps.
            Add selection to previous selections. '''
        ps = self._get_ps()
        self._selected_ps = select_ps(ps, selection, self._logger)

        if self._selection:
            self._selection |= selection
        else:
            self._selection = selection

    def get_selection(self):
        ''' Return dict of accumulated selections '''
        return self._selection

    def clear_selection(self):
        ''' Clear previous selections and use original ps '''
        self._selection = None
        self._selected_ps = None

    def get_vis_stats(self, selection, vis_axis):
        stats_ps = select_ps(self._ps, selection, self._logger)
        data_group = selection['data_group'] if 'data_group' in selection else 'base'
        return calculate_ps_stats(stats_ps, self._zarr_path, vis_axis, data_group, self._logger)

    def get_correlated_data(self, data_group):
        return get_correlated_data(self._get_ps().get(0), data_group)

    def get_raster_data(self, plot_inputs):
        return raster_data(self._get_ps(),
            plot_inputs,
            self._logger
        )

    def _get_ps(self):
        ''' Returns selected ps if selection has been done, else original ps '''
        return self._selected_ps if self._selected_ps else self._ps

    def _get_unique_values(self, df_col):
        ''' Return unique values in pandas Dataframe column, for summary '''
        values = df_col.to_numpy()
        try:
            # numeric arrays
            return np.unique(np.concatenate(values))
        except ValueError:
            # string arrays
            all_values = [row[0] for row in values]
            return np.unique(np.concatenate(all_values))
