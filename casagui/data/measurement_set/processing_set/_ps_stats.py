'''
   Calculate statistics on xradio ProcessingSet data.
'''

import dask
import numpy as np

from xradio.measurement_set.load_processing_set import ProcessingSetIterator
from graphviper.graph_tools import generate_dask_workflow
from graphviper.graph_tools.coordinate_utils import make_parallel_coord, interpolate_data_coords_onto_parallel_coords
from graphviper.graph_tools.map import map as graph_map
from graphviper.graph_tools.reduce import reduce as graph_reduce

try:
    from toolviper.dask.client import get_client
    _HAVE_TOOLVIPER = True
except ImportError:
    _HAVE_TOOLVIPER = False

from casagui.data.measurement_set.processing_set._xds_data import get_correlated_data, get_axis_data

def calculate_ps_stats(ps_xdt, ps_store, vis_axis, data_group, logger):
    '''
        Calculate stats for unflagged visibilities: min, max, mean, std
        ps_xdt (xarray.DataTree): input MeasurementSet opened from zarr file
        ps_store (str): path to visibility zarr file
        vis_axis (str): complex component (amp, phase, real, imag)
        Returns: stats tuple (min, max, mean, stddev) or None if all data flagged (count=0)
    '''
    input_params = {}
    input_params['input_data_store'] = ps_store
    input_params['xdt'] = ps_xdt
    input_params['vis_axis'] = vis_axis
    input_params['data_group'] = data_group
    for ms_xdt in ps_xdt.values():
        if data_group in ms_xdt.attrs['data_groups']:
            input_params['correlated_data'] = get_correlated_data(ms_xdt.ds, data_group)
            break

    if _HAVE_TOOLVIPER:
        active_client = get_client() # could be None if not set up outside casagui
    else:
        active_client = None
    n_threads = active_client.thread_info()['n_threads'] if active_client is not None else 4
    logger.debug(f"Setting {n_threads} n_chunks for parallel coords.")
    mapping = _get_task_data_mapping(ps_xdt, n_threads)

    data_min, data_max, data_mean = _calc_basic_stats(ps_xdt, mapping, input_params, logger)
    if np.isfinite(data_mean):
        input_params['mean'] = data_mean
        data_stddev = _calc_stddev(ps_xdt, mapping, input_params, logger)
        return data_min, data_max, data_mean, data_stddev
    return None

def _get_task_data_mapping(ps_xdt, n_threads):
    frequencies = ps_xdt.xr_ps.get_freq_axis()
    parallel_coords = {"frequency": make_parallel_coord(coord=frequencies, n_chunks=n_threads)}
    return interpolate_data_coords_onto_parallel_coords(parallel_coords, ps_xdt)

def _calc_basic_stats(ps_xdt, mapping, input_params, logger):
    ''' Calculate min, max, mean using graph map/reduce '''
    graph = graph_map(
        input_data=ps_xdt,
        node_task_data_mapping=mapping,
        node_task=_map_stats,
        input_params=input_params
    )
    reduce_map = graph_reduce(
        graph, _reduce_stats, input_params, mode='tree'
    )
    dask_graph = generate_dask_workflow(reduce_map)
    #dask_graph.visualize(filename='stats.png')
    results = dask.compute(dask_graph)

    data_min, data_max, data_sum, data_count = results[0]
    if data_count == 0.0:
        logger.debug("stats: no unflagged data")
        return (data_min, data_max, np.inf)

    data_mean = data_sum / data_count
    logger.debug(f"basic stats: min={data_min:.4f}, max={data_max:.4f}, sum={data_sum:.4f}, count={data_count} mean={data_mean:.4f}")
    return data_min, data_max, data_mean

def _calc_stddev(ps_xdt, mapping, input_params, logger):
    ''' Calculate stddev using graph map/reduce '''
    graph = graph_map(
        input_data=ps_xdt,
        node_task_data_mapping=mapping,
        node_task=_map_variance,
        input_params=input_params
    )
    reduce_map = graph_reduce(
        graph, _reduce_variance, input_params, mode='tree'
    )
    dask_graph = generate_dask_workflow(reduce_map)
    results = dask.compute(dask_graph)

    var_sum, var_count = results[0]
    data_variance = var_sum / var_count
    data_stddev = data_variance ** 0.5
    logger.debug(f"stats: variance={data_variance:.4f}, stddev={data_stddev:.4f}")
    return data_stddev

def _get_stats_xda(xds, vis_axis, data_group):
    ''' Return xda with only unflagged cross-corr visibility data '''
    # apply flags to get unflagged vis data
    xda = get_axis_data(xds, vis_axis, data_group)
    unflagged_xda = xda.where(np.logical_not(xds.FLAG))

    if unflagged_xda.count() > 0 and "baseline_antenna1_name" in unflagged_xda.coords:
        # if unflagged data, remove autocorrelation baselines
        stats_xda = unflagged_xda.where(
            unflagged_xda.baseline_antenna1_name != unflagged_xda.baseline_antenna2_name
        )
        if stats_xda.count() > 0:
            # return xda with nan where flagged or auto-corr
            return stats_xda

    # return xda with nan where flagged
    return unflagged_xda

def _map_stats(input_params):
    ''' Return min, max, sum, and count of data chunk '''
    vis_axis = input_params['vis_axis']
    data_group = input_params['data_group']
    correlated_data = input_params['correlated_data']
    min_vals = []
    max_vals = []
    sum_vals = []
    count_vals = []

    ps_iter = ProcessingSetIterator(
        input_params['data_selection'],
        input_params['input_data_store'],
        input_params['xdt'],
        input_params['data_group'],
        include_variables=[correlated_data, 'FLAG'],
        load_sub_datasets=False
    )

    for xds in ps_iter:
        xda = _get_stats_xda(xds, vis_axis, data_group)
        if xda.count() > 0:
            xda_data = xda.values.ravel()
            try:
                min_vals.append(xda_data[np.nanargmin(xda_data)])
            except ValueError:
                pass
            try:
                max_vals.append(xda_data[np.nanargmax(xda_data)])
            except ValueError:
                pass
            sum_vals.append(np.nansum(xda))
            count_vals.append(xda.count().values)
    try:
        min_value = np.nanmin(min_vals)
    except ValueError:
        min_value = np.nan
    try:
        max_value = np.nanmax(max_vals)
    except ValueError:
        max_value = np.nan
    return (min_value, max_value, sum(sum_vals), sum(count_vals))

# pylint: disable=unused-argument
def _reduce_stats(graph_inputs, input_params):
    ''' Compute min, max, sum, and count of all data.
        input_parameters seems to be required although unused. '''
    data_min = 0.0
    mins = [values[0] for values in graph_inputs]
    if not np.isnan(mins).all():
        data_min = min(0.0, np.nanmin(mins))

    data_max = 0.0
    maxs = [values[1] for values in graph_inputs]
    if not np.isnan(maxs).all():
        data_max = max(0.0, np.nanmax(maxs))

    data_sum = sum(values[2] for values in graph_inputs)
    data_count = sum(values[3] for values in graph_inputs)
    return (data_min, data_max, data_sum, data_count)
# pylint: enable=unused-argument

def _map_variance(input_params):
    ''' Return sum, count, of (xda - mean) squared '''
    vis_axis = input_params['vis_axis']
    data_group = input_params['data_group']
    correlated_data = input_params['correlated_data']
    mean = input_params['mean']

    sq_diff_sum = 0.0
    sq_diff_count = 0

    ps_iter = ProcessingSetIterator(
        input_params['data_selection'],
        input_params['input_data_store'],
        input_params['xdt'],
        input_params['data_group'],
        include_variables=[correlated_data, 'FLAG'],
        load_sub_datasets=False
    )

    for xds in ps_iter:
        xda = _get_stats_xda(xds, vis_axis, data_group)
        if xda.size > 0:
            sq_diff = (xda - mean) ** 2
            sq_diff_sum += np.nansum(sq_diff)
            sq_diff_count += sq_diff.count().values
    return (sq_diff_sum, sq_diff_count)

# pylint: disable=unused-argument
def _reduce_variance(graph_inputs, input_params):
    ''' Compute sum and count of all (xda-mean) squared data.
        input_parameters seems to be required although unused. '''
    sq_diff_sum = sum(values[0] for values in graph_inputs)
    sq_diff_count = sum(values[1] for values in graph_inputs)
    return (sq_diff_sum, sq_diff_count)
# pylint: enable=unused-argument
