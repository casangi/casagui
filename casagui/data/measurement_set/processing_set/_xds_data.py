''' Get MeasurementSet data from xarray Dataset '''

from astropy import constants
import numpy as np
import xarray as xr

from casagui.plot.ms_plot._ms_plot_constants import SPECTRUM_AXIS_OPTIONS, UVW_AXIS_OPTIONS, VIS_AXIS_OPTIONS, WEIGHT_AXIS_OPTIONS

def get_correlated_data(xds, data_group):
    ''' Return correlated_data value in data_group dict '''
    return xds.attrs['data_groups'][data_group]['correlated_data']

def get_axis_data(xds, axis, data_group=None):
    ''' Get requested axis data from xarray dataset.
            xds (dict): msv4 xarray.Dataset
            axis (str): axis data to retrieve.
            data_group (str): correlated data group name.
        Returns:    xarray.DataArray
    '''
    group_info = xds.data_groups[data_group]
    xda = None
    if _is_coordinate_axis(axis):
        xda = xds[axis]
    elif _is_antenna_axis(axis):
        xda = _get_antenna_axis(xds, axis)
    elif _is_vis_axis(axis):
        xda = _calc_vis_axis(xds, axis, group_info)
    elif _is_uvw_axis(axis):
        xda = _calc_uvw_axis(xds, axis, group_info)
    elif _is_weight_axis(axis):
        xda = _calc_weight_axis(xds, axis, group_info)
    elif 'spw' in axis:
        xda = _get_spw_axis(xds, axis)
    elif 'wave' in axis:
        xda = _calc_wave_axis(xds, axis, group_info)
    elif axis == 'field':
        xda = xr.DataArray([xds[group_info['correlated_data']].field_and_source_xds.field_name])
    elif axis == 'flag':
        xda = xds[group_info['flag']]
    elif axis == 'intents':
        xda = xr.DataArray(["".join(xds.partition_info['intents'])])
    elif axis == 'channel':
        xda = xr.DataArray(np.array(range(xds.frequency.size)))
    return xda

def _is_coordinate_axis(axis):
    return axis in ['scan_number', 'time', 'frequency', 'polarization',
        #'velocity': 'frequency', # calculate
        # TODO?
        #'observation':  no id, xds.observation_info (observer, project, release date)
        #'feed1':  no id, xds.antenna_xds
        #'feed2':  no id, xds.antenna_xds
    ]

def _is_vis_axis(axis):
    return axis in VIS_AXIS_OPTIONS

def _is_uvw_axis(axis):
    return axis in UVW_AXIS_OPTIONS

def _is_antenna_axis(axis):
    return 'baseline' in axis or 'antenna' in axis

def _is_weight_axis(axis):
    return axis in WEIGHT_AXIS_OPTIONS

def _get_spw_axis(xds, axis):
    if axis == 'spw_id':
        return xr.DataArray([xds.frequency.spectral_window_id])
    if axis == 'spw_name':
        return xr.DataArray([xds.frequency.spectral_window_name])
    raise ValueError(f"Invalid spw axis {axis}")

def _calc_vis_axis(xds, axis, group_info):
    ''' Calculate axis from correlated data '''
    correlated_data = group_info['correlated_data']
    xda = xds[correlated_data]

    # Single dish spectrum
    if correlated_data == "SPECTRUM":
        if axis in SPECTRUM_AXIS_OPTIONS:
            return xda.assign_attrs(units='Jy')
        raise RuntimeError(f"Vis axis {axis} invalid for SPECTRUM dataset, select from {SPECTRUM_AXIS_OPTIONS}")

    # Interferometry visibilities
    if axis == 'amp':
        return np.absolute(xda).assign_attrs(units='Jy')
    if axis == 'phase':
        # np.angle(xda) returns ndarray not xr.DataArray
        return (np.arctan2(xda.imag, xda.real) * 180.0/np.pi).assign_attrs(units="deg")
    if axis == 'real':
        return np.real(xda.assign_attrs(units='Jy'))
    if axis == 'imag':
        return np.imag(xda.assign_attrs(units='Jy'))
    return None

def _calc_uvw_axis(xds, axis, group_info):
    ''' Calculate axis from UVW xarray DataArray '''
    if 'uvw' not in group_info:
        raise RuntimeError(f"Axis {axis} is not valid in this dataset, no uvw data")

    uvw_xda = xds[group_info['uvw']]

    if axis == 'u':
        return uvw_xda.isel(uvw_label=0)
    if axis == 'v':
        return uvw_xda.isel(uvw_label=1)
    if axis == 'w':
        return uvw_xda.isel(uvw_label=2)

    # uvdist
    u_xda = uvw_xda.isel(uvw_label=0)
    v_xda = uvw_xda.isel(uvw_label=1)
    return np.sqrt(np.square(u_xda) + np.square(v_xda))

def _calc_wave_axis(xds, axis, group_info):
    wave_axes = {'uwave': 'u', 'vwave': 'v', 'wwave': 'w', 'uvwave': 'uvdist'}
    if axis not in wave_axes:
        raise ValueError(f"Invalid wave axis {axis}")
    uvwdist_array = _calc_uvw_axis(xds, wave_axes[axis], group_info).values / constants.c
    uvwdist_len = len(uvwdist_array)
    freq_array = xds.frequency.values
    wave = np.zeros(shape=(len(freq_array), uvwdist_len), dtype=np.double)

    for i, in range(uvwdist_len):
        wave[:, i] = uvwdist_array[i] * freq_array

    wave_xda = xr.DataArray(wave, dims=['frequency', 'uvw_label'])
    return wave_xda

def _calc_weight_axis(xds, axis, group_info):
    weight = xds[group_info['weight']]
    if axis == 'weight':
        return weight
    return np.sqrt(1.0 / weight)

def _get_antenna_axis(xds, axis):
    if 'antenna_name' in xds.coords:
        return xds.antenna_name

    if axis == 'antenna1':
        return xds.baseline_antenna1_name
    if axis == 'antenna2':
        return xds.baseline_antenna2_name
    if axis == 'baseline_id':
        return xds.baseline_id
    if axis == 'baseline':
        return xds.baseline
    raise ValueError(f"Invalid antenna/baseline axis {axis}")
