import dask
import numpy as np

from xradio.measurement_set.load_processing_set import ProcessingSetIterator
from graphviper.graph_tools import generate_dask_workflow
from graphviper.graph_tools.coordinate_utils import make_parallel_coord, interpolate_data_coords_onto_parallel_coords
from graphviper.graph_tools.map import map
from graphviper.graph_tools.reduce import reduce

try:
    from toolviper.dask.client import get_client
    _have_toolviper = True
except ImportError:
    _have_toolviper = False

from ._xds_data import get_correlated_data, get_axis_data

def calculate_ps_stats(ps, ps_store, vis_axis, data_group, logger):
    '''
        Calculate stats for unflagged visibilities: min, max, mean, std
        ps (msv4 processing set): visibility data with flags
        ps_store (str): path to visibility file
        vis_axis (str): component (amp, phase, real, imag) followed by optional type (corrected, model) e.g. amp_corrected
        Returns: stats tuple (data_min, data_max, data_mean, data_stddev)
    '''
    input_params = {}
    input_params['input_data_store'] = ps_store
    input_params['data_group'] = data_group
    input_params['correlated_data'] = get_correlated_data(ps.get(0), data_group)
    input_params['vis_axis'] = vis_axis

    if _have_toolviper:
        active_client = get_client() # could be None if not set up outside casagui
    else:
        active_client = None
    n_threads = active_client.thread_info()['n_threads'] if active_client is not None else 4
    logger.debug(f"Setting {n_threads} n_chunks for parallel coords.")

    # Calculate min, max, mean using frequency parallel coords
    frequencies = ps.get_ps_freq_axis()
    parallel_coords = {"frequency": make_parallel_coord(coord=frequencies, n_chunks=n_threads)}
    node_task_data_mapping = interpolate_data_coords_onto_parallel_coords(parallel_coords, ps)

    graph = map(
        input_data=ps,
        node_task_data_mapping=node_task_data_mapping,
        node_task=_map_stats,
        input_params=input_params
    )
    graph_reduce = reduce(
        graph, _reduce_stats, input_params, mode='tree'
    )
    dask_graph = generate_dask_workflow(graph_reduce)
    #dask_graph.visualize(filename='stats.png')
    results = dask.compute(dask_graph)
    data_min, data_max, data_sum, data_count = results[0]

    if data_count == 0.0:
        logger.debug("stats: no unflagged data")
        return (0.0, 0.0, 0.0, 0.0)

    data_mean = data_sum / data_count
    input_params['mean'] = data_mean
    logger.debug(f"stats: min={data_min:.4f}, max={data_max:.4f}, sum={data_sum:.4f}, count={data_count} mean={data_mean:.4f}")

    # Calculate variance and standard deviation
    graph = map(
        input_data=ps,
        node_task_data_mapping=node_task_data_mapping,
        node_task=_map_variance,
        input_params=input_params
    )
    graph_reduce = reduce(
        graph, _reduce_variance, input_params, mode='tree'
    )
    dask_graph = generate_dask_workflow(graph_reduce)
    results = dask.compute(dask_graph)
    var_sum, var_count = results[0]
    data_variance = var_sum / var_count
    data_stddev = data_variance ** 0.5
    logger.debug(f"stats: variance={data_variance:.4f}, stddev={data_stddev:.4f}")
    return (data_min, data_max, data_mean, data_stddev)

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
    data_group = input_params['data_group']
    correlated_data = input_params['correlated_data']
    vis_axis = input_params['vis_axis']
    min_vals = []
    max_vals = []
    sum_vals = []
    count_vals = []

    ps_iter = ProcessingSetIterator(
        input_params['data_selection'],
        input_params['input_data_store'],
        input_params['input_data'],
        data_variables=[correlated_data, 'FLAG'],
        load_sub_datasets=False
    )
 
    for xds in ps_iter:
        xda = _get_stats_xda(xds, vis_axis, data_group)
        if xda.count() > 0:
            xda_data = xda.values.ravel()
            try:
                min_val = xda_data[np.nanargmin(xda_data)]
                min_vals.append(min_val)
            except ValueError:
                pass
            try:
                max_val = xda_data[np.nanargmax(xda_data)]
                max_vals.append(max_val)
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
    result = (min_value, max_value, sum(sum_vals), sum(count_vals))
    return result

def _reduce_stats(graph_inputs, input_params):
    ''' Compute min, max, sum, and count of all data'''
    data_min = 0.0
    mins = [input[0] for input in graph_inputs]
    if not np.isnan(mins).all():
        data_min = min(0.0, np.nanmin(mins))

    data_max = 0.0
    maxs = [input[1] for input in graph_inputs]
    if not np.isnan(maxs).all():
        data_max = max(0.0, np.nanmax(maxs))

    data_sum = sum([input[2] for input in graph_inputs])
    data_count = sum([input[3] for input in graph_inputs])
    return (data_min, data_max, data_sum, data_count)

def _map_variance(input_params):
    ''' Return sum, count, of (xda - mean) squared '''
    data_group = input_params['data_group']
    correlated_data = input_params['correlated_data']
    vis_axis = input_params['vis_axis']
    mean = input_params['mean']

    sq_diff_sum = 0.0
    sq_diff_count = 0

    ps_iter = ProcessingSetIterator(
        input_params['data_selection'],
        input_params['input_data_store'],
        input_params['input_data'],
        data_variables=[correlated_data, 'FLAG'],
        load_sub_datasets=False
    )

    for xds in ps_iter:
        xda = _get_stats_xda(xds, vis_axis, data_group)
        if xda.size > 0:
            sq_diff = (xda - mean) ** 2
            sq_diff_sum += np.nansum(sq_diff)
            sq_diff_count += sq_diff.count().values
    return (sq_diff_sum, sq_diff_count)
 
def _reduce_variance(graph_inputs, input_params):
    ''' Compute sum and count of all (xda-mean) squared data'''
    sq_diff_sum = sum([input[0] for input in graph_inputs])
    sq_diff_count = sum([input[1] for input in graph_inputs])
    return (sq_diff_sum, sq_diff_count)
