'''
MeasurementSet data backend using xradio Processing Set.
'''

import numpy as np
import pandas as pd

try:
    from casagui.data.measurement_set.processing_set._ps_io import get_processing_set
    _HAVE_XRADIO = True
    from casagui.data.measurement_set.processing_set._ps_coords import set_coordinates
    from casagui.data.measurement_set.processing_set._ps_select import select_ps
    from casagui.data.measurement_set.processing_set._ps_stats import calculate_ps_stats
    from casagui.data.measurement_set.processing_set._ps_raster_data import raster_data
    from casagui.data.measurement_set.processing_set._xds_data import get_correlated_data
except ImportError as e:
    _HAVE_XRADIO = False


class PsData:
    '''
    Class implementing data backend using xradio Processing Set for accessing and selecting MeasurementSet data.
    '''

    def __init__(self, ms, logger):
        if not _HAVE_XRADIO:
            raise RuntimeError("xradio package not available for reading MeasurementSet")

        if not ms:
            raise RuntimeError("MS path not available for reading MeasurementSet")

        # Convert msv2 to msv4 if ms path is not zarr
        self._ps, self._zarr_path = get_processing_set(ms, logger)
        self._logger = logger

        # Convert units, create "baseline" coordinate from "baseline_id" and antenna names
        for name, xds in self._ps.items():
            self._ps[name] = set_coordinates(xds)

        self._selection = {}
        self._selected_ps = None # cumulative selection
        self._iter_selected_ps = None # not cumulative selection

    def get_path(self):
        ''' Return path to zarr file (input or converted from msv2) '''
        return self._zarr_path

    def summary(self, columns=None):
        ''' Print full or selected summary of Processing Set metadata, optionally by msv4 '''
        pd.set_option("display.max_rows", len(self._ps))
        pd.set_option("display.max_columns", 12)
        ps_summary = self._ps.summary()

        if columns is None:
            print(ps_summary)
        elif columns == "by_msv4":
            for row in ps_summary.itertuples(index=False):
                print("-----")
                print(f"MSv4 name: {row[0]}")
                print(f"intent: {row[1]}")
                shape = row[2]
                print(f"shape: {shape[0]} times, {shape[1]} baselines, {shape[2]} channels, {shape[3]} polarizations")
                print(f"polarization: {row[3]}")
                print(f"scan_number: {row[4]}")
                print(f"spw_name: {row[5]}")
                print(f"field_name: {row[6]}")
                print(f"source_name: {row[7]}")
                print(f"line_name: {row[8]}")
                field_coords = row[9]
                print(f"field_coords: ({field_coords[0]}) {field_coords[1]} {field_coords[2]}")
                print(f"frequency range: {row[10]:e} - {row[11]:e}")
            print("-----")
        else:
            if isinstance(columns, str):
                columns = [columns]
            col_df = ps_summary[columns]
            print(col_df)

    def get_data_groups(self):
        ''' Returns set of data group names in Processing Set data. '''
        data_groups = []
        for xds_name in self._ps:
            data_groups.extend(list(self._ps[xds_name].data_groups))
        return set(data_groups)

    def get_antennas(self, plot_positions=False):
        ''' Returns list of antenna names in ProcessingSet antenna_xds.
                plot_positions (bool): Optionally show plot of antenna positions.
        '''
        if plot_positions:
            self._ps.plot_antenna_positions()
        return self._ps.get_combined_antenna_xds().antenna_name.values.tolist()

    def plot_phase_centers(self, label_all_fields=False, data_group='base'):
        ''' Plot the phase center locations of all fields in the Processing Set (original or selected) and label central field.
                label_all_fields (bool); label all fields on the plot
                data_group (str); data group to use for processing.
        '''
        self._ps.plot_phase_centers(label_all_fields, data_group)

    def get_ps_len(self):
        ''' Returns number of MeasurementSetXds in ProcessingSet. '''
        return len(self._get_ps())

    def get_ps_max_dims(self):
        ''' Returns maximum length of data dimensions in all . '''
        ps = self._get_ps()
        return ps.get_ps_max_dims()

    def get_data_dimensions(self):
        ''' Return the maximum dimensions across all Measurement Sets in the Processing Set. '''
        max_dims = self.get_ps_max_dims()
        dims = list(max_dims.keys())
        if 'uvw_label' in dims:
            dims.remove('uvw_label')
        return dims

    def get_dimension_values(self, dimension):
        ''' Return sorted list of unique values for input dimension in ProcessingSet. '''
        ps = self._get_ps()
        dim_values = []
        for xds in ps.values():
            try:
                dim_values.extend([value.item() for value in xds[dimension].values])
            except TypeError:
                dim_values.append(xds[dimension].values.item())
        return sorted(set(dim_values))

    def get_dimension_attrs(self, dim):
        ''' Return attributes dict for input dimension in ProcessingSet. '''
        ps = self._get_ps()
        return ps.get(0)[dim].attrs

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
        start_freq = spw_df.at[spw_df.index[0], 'start_frequency']
        end_freq = spw_df.at[spw_df.index[0], 'end_frequency']
        self._logger.info(f"Selecting first spw {first_spw_name} (id {first_spw_id}) with frequency range {start_freq:e} - {end_freq:e}")
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

    def clear_selection(self):
        ''' Clear previous selections and use original ps '''
        self._selection = None
        self._selected_ps = None

    def get_vis_stats(self, selection, vis_axis):
        ''' Returns statistics (min, max, mean, std) for data selected by selection.
                selection (dict): fields and values to select
        '''
        stats_ps = select_ps(self._ps, selection, self._logger)
        data_group = selection['data_group'] if 'data_group' in selection else 'base'
        return calculate_ps_stats(stats_ps, self._zarr_path, vis_axis, data_group, self._logger)

    def get_correlated_data(self, data_group):
        ''' Returns name of 'correlated_data' in Processing Set data_group '''
        return get_correlated_data(self._get_ps().get(0), data_group)

    def get_raster_data(self, plot_inputs):
        ''' Returns xarray Dataset after applying plot inputs and raster plane selection '''
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
