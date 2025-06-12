'''
    Class for accessing and selecting MeasurementSet data using a data backend.
'''

from casagui.data.measurement_set.processing_set._ps_data import PsData

class MsData:
    '''
    Access and select MeasurementSet data.
    Current backend implementation is PsData using xradio Processing Set.
    '''

    def __init__(self, ms_path, logger):
        self._ms_path = ms_path
        self._logger = logger
        self._data = None
        self._data_initialized = False
        self._init_data(ms_path)

    def is_valid(self):
        ''' Returns whether MS path has been set so data can be accessed. '''
        return self._data_initialized

    def is_ms_path(self, path):
        ''' Check if input path matches input ms path or zarr path '''
        return path == self.get_path() or path == self._ms_path

    def get_path(self):
        ''' Returns path of MS/zarr file or None if not set. '''
        if self._data_initialized:
            return self._data.get_path() # path to zarr file
        if self._ms_path:
            return self._ms_path # path to ms v2
        return None

    def summary(self, data_group='base', columns=None):
        ''' Print summary of Processing Set data.
                columns (None, str, list): type of metadata to list.
                    None:      Print all summary columns in ProcessingSet.
                    'by_msv4': Print formatted summary metadata by MSv4.
                    str, list: Print a subset of summary columns in ProcessingSet.
                        Options: 'name', 'intents', 'shape', 'polarization', 'scan_number', 'spw_name',
                                 'field_name, 'source_name', 'field_coords', 'start_frequency', 'end_frequency'
        '''
        # ProcessingSet function
        if self._data_initialized:
            self._data.summary(data_group, columns)
        else:
            self._log_no_ms()

    def get_ps_summary(self):
        ''' Return Pandas DataFrame summary of ProcessingSet '''
        if self._data_initialized:
            return self._data.get_summary()
        self._log_no_ms()
        return None

    def data_groups(self):
        ''' Returns set of data group names in Processing Set data. '''
        # ProcessingSet function
        if self._data_initialized:
            return self._data.get_data_groups()
        self._log_no_ms()
        return None

    def get_antennas(self, plot_positions=False, label_antennas=False):
        ''' Returns list of antenna names in data.
                plot_positions (bool): show plot of antenna positions.
                label_antennas (bool): label positions with antenna names.
        '''
        # Antenna positions plot is ProcessingSet function
        if self._data_initialized:
            return self._data.get_antennas(plot_positions, label_antennas)
        self._log_no_ms()
        return None

    def plot_phase_centers(self, data_group='base', label_all_fields=False):
        ''' Plot the phase center locations of all fields in the Processing Set (original or selected) and label central field.
                label_all_fields (bool); label all fields on the plot
                data_group (str); data group to use for processing.
        '''
        # ProcessingSet function
        if self._data_initialized:
            self._data.plot_phase_centers(label_all_fields, data_group)
        else:
            self._log_no_ms()

    def get_num_ms(self):
        ''' Returns number of MeasurementSets in data. '''
        if self._data_initialized:
            return self._data.get_ps_len()
        self._log_no_ms()
        return None

    def get_max_data_dims(self):
        ''' Returns maximum length of dimensions in data. '''
        if self._data_initialized:
            return self._data.get_max_dims()
        self._log_no_ms()
        return None

    def get_data_dimensions(self):
        ''' Returns names of data dimensions. '''
        if self._data_initialized:
            return self._data.get_data_dimensions()
        self._log_no_ms()
        return None

    def get_dimension_values(self, dim):
        ''' Return values for dimension in current data.
                dim (str): dimension name
        '''
        if self._data_initialized:
            return self._data.get_dimension_values(dim)
        self._log_no_ms()
        return None

    def get_dimension_attrs(self, dim):
        ''' Return dict of data attributes for dimension.
                dim (str): dimension name
        '''
        if self._data_initialized:
            return self._data.get_dimension_attrs(dim)
        self._log_no_ms()
        return None

    def get_first_spw(self):
        ''' Returns name of first spw by id. '''
        if self._data_initialized:
            return self._data.get_first_spw()
        self._log_no_ms()
        return None

    def select_data(self, selection):
        ''' Apply selection in data.
                selection (dict): fields and values to select
        '''
        if self._data_initialized:
            self._data.select_data(selection)
        else:
            self._log_no_ms()

    def clear_selection(self):
        ''' Clears selection dict and selected data. '''
        if self._data_initialized:
            self._data.clear_selection()

    def get_vis_stats(self, selection, vis_axis):
        ''' Returns statistics (min, max, mean, std) for data selected by selection.
                selection (dict): fields and values to select
        '''
        if self._data_initialized:
            return self._data.get_vis_stats(selection, vis_axis)
        self._log_no_ms()
        return None

    def get_correlated_data(self, data_group):
        ''' Returns name of correlated data variable in Processing Set data group '''
        if self._data_initialized:
            return self._data.get_correlated_data(data_group)
        self._log_no_ms()
        return None

    def get_raster_data(self, plot_inputs):
        ''' Returns xarray Dataset after applying plot inputs and raster plane selection '''
        if self._data_initialized:
            return self._data.get_raster_data(plot_inputs)
        self._log_no_ms()
        return None

    def _log_no_ms(self):
        self._logger.info("No MS path set, cannot access data")

    def _init_data(self, ms_path):
        ''' Data backend for MeasurementSet; currently xradio ProcessingSet '''
        if ms_path:
            self._data = PsData(ms_path, self._logger)
            self._data_initialized = True
