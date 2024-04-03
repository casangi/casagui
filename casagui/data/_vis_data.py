import numpy as np
from astropy.constants import c

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
        # VISIBILITIES and FLAGS
        'amp': 'VISIBILITY',
        'phase': 'VISIBILITY',
        'real': 'VISIBILITY',
        'imag': 'VISIBILITY',
        'amp_corrected': 'VISIBILITY_CORRECTED',
        'phase_corrected': 'VISIBILITY_CORRECTED',
        'real_corrected': 'VISIBILITY_CORRECTED',
        'imag_corrected': 'VISIBILITY_CORRECTED',
        #'weight': not in xradio
        #'wtxamp': not in xradio
        #'wtsp': not in xradio
        #'sigma': 'not in xradio
        #'sigmasp': 'not in xradio
        'flag': 'FLAG',
        # OBSERVATIONAL GEOMETRY
        'u': 'UVW',
        'v': 'UVW',
        'w': 'UVW',
        'uvdist': 'UVW',
    }

    wave_axis_to_xds = {
        'uwave': ('u', 'frequency'),
        'vwave': ('v', 'frequency'),
        'wwave': ('w', 'frequency'),
        'uvwave': ('uvdist', 'frequency')
    }

    if axis in wave_axis_to_xds.keys():
        xda_list = []
        for axis_component in wave_axis_to_xds[axis]:
            xda_list.append(get_vis_axis_data(xds, axis_component))
        data_xda = _calc_wave_axis(xda_list, axis)
    else:
        if axis not in axis_to_xds.keys():
            raise RuntimeError(f"axis {axis_component} invalid for dataset")
        location = axis_to_xds[axis]
        if isinstance(location, str):
            if location in xds.attrs.keys():
                xda = xds.attrs[location[0]]
            else:
                xda = xds[location]
        else: # tuple
            xda = xds[location[0]].attrs[location[1]]
            if len(location) == 3:
                xda = value[location[2]]

        if axis in ['amp', 'phase', 'real', 'imag']:
            data_xda = _calc_vis_axis(xda, axis)
        elif axis == 'chan':
            data_xda = xr.DataArray(np.array(range(xda.size)), dtype=np.int32)
        elif axis in ['u', 'v', 'w', 'uvdist']:
            data_xda = _calc_uvw_axis(xda, axis)
        else:
            data_xda = xda

    return data_xda

def _calc_vis_axis(vis_xda, axis):
    ''' Calculate axis from VISIBILITY xarray DataArray '''
    if axis == 'amp':
        return np.absolute(vis_xda).assign_attrs(units='Jy')
    elif axis == 'phase':
        # np.angle(vis_xda) returns ndarray not xr.DataArray
        return (np.arctan2(vis_xda.imag, vis_xda.real) * 180/np.pi).assign_attrs(units="deg")
    elif axis == 'real':
        return np.real(vis_xda.assign_attrs(units='Jy'))
    elif axis == 'imag':
        return np.imag(vis_xda.assign_attrs(units='Jy'))

def _calc_uvw_axis(uvw_xda, axis):
    ''' Calculate axis from UVW xarray DataArray '''
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

def _calc_wave_axis(xda_list, axis):
    ''' Calculate axis from multiple xarray DataArrays '''
    uvwdist_array = xda_list[0].values / c  # u, v, w, or uvdist, depending on axis
    freq_array = xda_list[1].values

    wave = np.zeros(shape=(len(freq_array), len(uvwdist_array)), dtype=np.double)
    for i in range(len(uvwdist_array)):
        wave[:, i] = uvwdist_array[i] * freq_array

    wave_xda = xr.DataArray(wave, dims=['frequency', 'uvw_index'])
    return wave_xda
