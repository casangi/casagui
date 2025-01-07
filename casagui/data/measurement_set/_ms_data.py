''' Get MeasurementSet data from xarray Dataset '''

import numpy as np
import xarray as xr
from astropy.constants import c
from pandas import to_datetime

from xradio.measurement_set.processing_set import ProcessingSet

def is_vis_axis(axis):
    return axis in ['amp', 'phase', 'real', 'imag']

def get_correlated_data(xds, data_group):
    return xds.attrs['data_groups'][data_group]['correlated_data']

def get_axis_data(xds, axis, data_group=None):
    ''' Get requested axis data from xarray dataset.
    xds (dict): msv4 xarray.Dataset
    axis (str): axis data to retrieve.
    returns:    xarray.DataArray
    '''

    group_info = xds.data_groups[data_group]

    if _is_coordinate_axis(axis):
        return xds[axis]
    elif axis == 'channel':
        return xr.DataArray(np.array(range(xds.frequency.size)), dtype=np.int32)
    elif axis == 'field':
        return xr.DataArray([xds[group_info['correlated_data']].field_and_source_xds.field_name])
    elif axis == 'flag':
        return xds[group_info['flag']]
    elif axis == 'intents':
        return xr.DataArray(["".join(xds.partition_info['intents'])])
    elif 'spw' in axis:
        return _get_spw_axis(xds, axis)
    elif _is_antenna_axis(axis):
        return _get_antenna_axis(xds, axis)
    elif is_vis_axis(axis):
        return _calc_vis_axis(xds, axis, group_info['correlated_data'])
    elif _is_uvw_axis(axis):
        if 'uvw' in group_info:
            return _calc_uvw_axis(xds, axis, group_info['uvw'])
        raise RuntimeError("Axis {} is not valid in this dataset, no uvw data", axis) 
    elif 'wave' in axis:
        return _calc_wave_axis(xds, axis, group_info['uvw'])
    elif _is_weight_axis(axis):
        return _calc_weight_axis(xds, axis)
    else:
        raise ValueError(f"Invalid/unsupported axis {axis}")

def _is_coordinate_axis(axis):
    return axis in ['scan_number', 'time', 'frequency', 'polarization',
        #'velocity': 'frequency', # calculate
        # TODO?
        #'observation':  no id, xds.observation_info (observer, project, release date)
        #'feed1':  no id, xds.antenna_xds
        #'feed2':  no id, xds.antenna_xds
    ]

def _is_uvw_axis(axis):
    return axis in ['u', 'v', 'w', 'uvdist']

def _is_antenna_axis(axis):
    return 'baseline' in axis or 'antenna' in axis

def _is_weight_axis(axis):
    return axis in ['weight', 'sigma']

def _get_spw_axis(xds, axis):
    if axis == 'spw_id':
        return xr.DataArray([xds.frequency.spectral_window_id])
    elif axis == 'spw_name':
        return xr.DataArray([xds.frequency.spectral_window_name])
    raise ValueError(f"Invalid spw axis {axis}")

def _calc_vis_axis(xds, axis, correlated_data):
    ''' Calculate axis from correlated data '''
    xda = xds[correlated_data]

    # Single dish spectrum
    if correlated_data == "SPECTRUM":
        if axis in ['amp', 'real']:
            return xda.assign_attrs(units='Jy')
        raise RuntimeError(f"{axis} invalid for SPECTRUM dataset")

    # Interferometry visibilities
    if axis == 'amp':
        return np.absolute(xda).assign_attrs(units='Jy')
    elif axis == 'phase':
        # np.angle(xda) returns ndarray not xr.DataArray
        return (np.arctan2(xda.imag, xda.real) * 180.0/np.pi).assign_attrs(units="deg")
    elif axis == 'real':
        return np.real(xda.assign_attrs(units='Jy'))
    elif axis == 'imag':
        return np.imag(xda.assign_attrs(units='Jy'))
    return None

def _calc_uvw_axis(xds, axis, uvw_data):
    ''' Calculate axis from UVW xarray DataArray '''
    uvw_xda = xds[uvw_data]
    if axis == 'u':
        return uvw_xda.isel(uvw_label=0)
    elif axis == 'v':
        return uvw_xda.isel(uvw_label=1)
    elif axis == 'w':
        return uvw_xda.isel(uvw_label=2)
    else: # uvdist
        u_xda = uvw_xda.isel(uvw_label=0)
        v_xda = uvw_xda.isel(uvw_label=1)
        return np.sqrt(np.square(u_xda) + np.square(v_xda))

def _calc_wave_axis(xds, axis, uvw_data):
    wave_axes = {'uwave': 'u', 'vwave': 'v', 'wwave': 'w', 'uvwave': 'uvdist'}
    if axis not in wave_axes:
        raise ValueError(f"Invalid wave axis {axis}")

    uvwdist_array = _calc_uvw_axis(xds, wave_axes[axis], uvw_data).values / c
    freq_array = xds.frequency.values
    wave = np.zeros(shape=(len(freq_array), len(uvwdist_array)), dtype=np.double)

    for i in range(len(uvwdist_array)):
        wave[:, i] = uvwdist_array[i] * freq_array

    wave_xda = xr.DataArray(wave, dims=['frequency', 'uvw_label'])
    return wave_xda

def _calc_weight_axis(xds, axis):
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
