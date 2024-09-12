import numpy as np
from astropy.constants import c

from xradio.vis._processing_set import processing_set

def is_vis_axis(axis):
    vis_axes = ['amp', 'phase', 'real', 'imag']
    return axis.split('_')[0] in vis_axes


def get_vis_data_var(xds, vis_axis):
    ''' Returns name of xds data_var or raise exception '''
    if isinstance(xds, processing_set):
        xds = xds.get(0)

    vis_type = vis_axis.split('_')[1] if '_' in vis_axis else 'data'
    data_vars = {
        'data': 'VISIBILITY',
        'corrected': 'VISIBILITY_CORRECTED',
        'model': 'VISIBILITY_MODEL'
    }

    if vis_type not in data_vars:
        raise ValueError(f"Invalid vis axis type: {vis_type}")

    if "SPECTRUM" in xds.data_vars:
        return "SPECTRUM"

    return data_vars[vis_type]

def get_axis_data(xds, axis):
    ''' Get requested axis data from xarray dataset.
    xds (dict): msv4 xarray.Dataset
    axis (str): axis data to retrieve.
    returns:    xarray.DataArray
    '''
    axis_to_xds = {
        # METADATA
        #'field': ('VISIBILITY', 'field_info') # TODO concat loses field info
        'time': 'time',
        'interval': 'EFFECTIVE_INTEGRATION_TIME',
        #'spw': ('frequency', 'spw_id'), # TODO check if lose spw info
        'channel': 'frequency',
        'frequency': 'frequency',
        #'velocity': 'frequency', # calculate?
        'corr': 'polarization',
        'baseline': 'baseline_id',
        'antenna1': 'baseline_antenna1_id',
        'antenna2': 'baseline_antenna2_id',
        #'observation':  not in xradio
        'intent': 'intent',
        #'feed1':  not in xradio (single dish?)
        #'feed2':  not in xradio (single dish?)
        #'weight': not in xradio
        #'wtxamp': not in xradio
        #'wtsp': not in xradio
        #'sigma': 'not in xradio
        #'sigmasp': 'not in xradio
        'flag': 'FLAG',
    }

    if is_vis_axis(axis):
        return _calc_vis_axis(xds, axis)
    elif axis in ['u', 'v', 'w', 'uvdist']:
        return _calc_uvw_axis(xds, axis)
    elif 'wave' in axis:
        return _calc_wave_axis(xds, axis)
    elif axis in axis_to_xds:
        location = axis_to_xds[axis]
        if location in xds.attrs:
            xda = xds.attrs[location]
        else:
            xda = xds[location]

        if axis == 'chan':
            return xr.DataArray(np.array(range(xda.size)), dtype=np.int32)
        else:
            return xda
    else:
        raise ValueError(f"Invalid/unsupported axis {axis}")


def _calc_vis_axis(xds, axis):
    ''' Calculate axis from VISIBILITY xarray DataArray '''
    data_var = get_vis_data_var(xds, axis)
    if data_var not in xds.data_vars:
        raise ValueError(f"Invalid/unsupported axis {axis} for dataset")
    xda = xds[data_var]

    # Single dish
    if data_var == "SPECTRUM":
        if axis in ['amp', 'real']:
            return xda.assign_attrs(units='Jy')
        raise ValueError(f"{axis} invalid for SPECTRUM dataset")

    # Interferometry
    if 'amp' in axis:
        return np.absolute(xda).assign_attrs(units='Jy')
    elif 'phase' in axis:
        # np.angle(xda) returns ndarray not xr.DataArray
        return (np.arctan2(xda.imag, xda.real) * 180.0/np.pi).assign_attrs(units="deg")
    elif 'real' in axis:
        return np.real(xda.assign_attrs(units='Jy'))
    elif 'imag' in axis:
        return np.imag(xda.assign_attrs(units='Jy'))
    return None
    

def _calc_uvw_axis(xds, axis):
    ''' Calculate axis from UVW xarray DataArray '''
    uvw_xda = xds['UVW']
    if axis == 'u':
        return uvw_xda.isel(uvw_label=0)
    elif axis == 'v':
        return uvw_xda.isel(uvw_label=1)
    elif axis == 'w':
        return uvw_xda.isel(uvw_label=2)
    else:
        u_xda = uvw_xda.isel(uvw_label=0)
        v_xda = uvw_xda.isel(uvw_label=1)
        return np.sqrt(u_xda**2 + v_xda**2)


def _calc_wave_axis(xds, axis):
    wave_axes = {
        'uwave': ('u', 'frequency'),
        'vwave': ('v', 'frequency'),
        'wwave': ('w', 'frequency'),
        'uvwave': ('uvdist', 'frequency')
    }
    if axis not in wave_axes:
        raise ValueError(f"Invalid/unsupported axis {axis}")
    components = wave_axes[axis]

    uvwdist_array = components[0].values / c
    freq_array = components[1].values
    wave = np.zeros(shape=(len(freq_array), len(uvwdist_array)), dtype=np.double)

    for i in range(len(uvwdist_array)):
        wave[:, i] = uvwdist_array[i] * freq_array

    wave_xda = xr.DataArray(wave, dims=['frequency', 'uvw_index'])
    return wave_xda
