from xradio.vis.load_processing_set import processing_set_iterator
from graphviper.dask.client import local_client
from graphviper.graph_tools import generate_dask_workflow
from graphviper.graph_tools.coordinate_utils import make_parallel_coord, interpolate_data_coords_onto_parallel_coords
from graphviper.graph_tools.map import map
from graphviper.graph_tools.reduce import reduce

import dask
from dask.distributed import client
import numpy as np

from ._vis_data import get_vis_data_var, get_axis_data

def calculate_vis_stats(ps, ps_store, vis_axis, logger):
    '''
        Calculate stats for unflagged visibilities: min, max, mean, std
        ps (msv4 processing set): visibility data with flags
        ps_store (str): path to visibility file
        vis_axis (str): component (amp, phase, real, imag) followed by optional type (corrected, model) e.g. amp_corrected
    '''
    vis_data = get_vis_data_var(vis_axis)
    if vis_data is None:
        raise RuntimeError(f"Invalid visibility axis {vis_axis}")

    input_params = {}
    input_params['input_data_store'] = ps_store
    input_params['vis_axis'] = vis_axis
    input_params['vis_data'] = vis_data

    active_client = client._get_global_client()
    if active_client is not None:
        n_threads = len(active_client.nthreads())
        logger.debug(f"vis stats: dask client has {n_threads} threads.")
    else:
        n_threads = 1
        logger.debug("vis stats: no dask client created.")
    #n_ddis = len(set(ps.summary()['spw_id']))
    #n_chunks = n_client_threads * n_ddis * 4
    n_chunks = max(n_threads, 8)
    logger.debug(f"Setting {n_chunks} n_chunks for parallel coords.")

    # Calculate min, max, mean using frequency parallel coords
    frequencies = ps.get_ps_freq_axis()
    parallel_coords = {"frequency": make_parallel_coord(coord=frequencies, n_chunks=n_chunks)}
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
    data_mean = data_sum / data_count
    input_params['mean'] = data_mean
    logger.debug(f"stats: min={data_min}, max={data_max}, sum={data_sum}, count={data_count}, mean={data_mean}")

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
    logger.debug(f"stats: variance={data_variance}, stddev={data_stddev}")
    return (data_min, data_max, data_mean, data_stddev)

def calculate_coord_min(ps, ps_store, coord):
    ''' Calculate minimum value of coord in ps '''
    input_params = {}
    input_params['input_data_store'] = ps_store
    input_params['coord'] = coord
    n_chunks = 8 

    # Calculate min, max, mean using frequency parallel coords
    frequencies = ps.get_ps_freq_axis()
    parallel_coords = {"frequency": make_parallel_coord(coord=frequencies, n_chunks=n_chunks)}
    node_task_data_mapping = interpolate_data_coords_onto_parallel_coords(parallel_coords, ps)

    graph = map(
        input_data=ps,
        node_task_data_mapping=node_task_data_mapping,
        node_task=_map_min,
        input_params=input_params
    )
    graph_reduce = reduce(
        graph, _reduce_min, input_params, mode='tree'
    )
    dask_graph = generate_dask_workflow(graph_reduce)
    results = dask.compute(dask_graph)
    return results[0]

def _get_stats_xda(xds, vis_axis):
    ''' Return xda with only unflagged cross-corr visibility data '''
    xda = get_axis_data(xds, vis_axis)
    # apply flags
    unflagged_xda = xda.where(np.logical_not(xds.FLAG))
    # remove autocorrelation baselines
    stats_xda = unflagged_xda.where(
        xds.baseline_antenna1_id != xds.baseline_antenna2_id,
        drop=True
    )
    if stats_xda.size == 0:
        stats_xda = unflagged_xda
    return stats_xda

def _map_stats(input_params):
    ''' Return min, max, sum, and count of data chunk '''
    vis_axis = input_params['vis_axis']
    vis_data = input_params['vis_data']
    min_vals = []
    max_vals = []
    sum_vals = []
    count_vals = []
    #print(f"data selection: {input_params['data_selection']}")

    ps_iter = processing_set_iterator(
        input_params['data_selection'],
        input_params['input_data_store'],
        input_params['input_data'],
        data_variables=[vis_data, 'FLAG'],
        load_sub_datasets=False
    )
 
    for xds in ps_iter:
        xda = _get_stats_xda(xds, vis_axis)
        if xda.size > 0:
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
        min_value = np.min(min_vals)
    except ValueError:
        min_value = np.nan
    try:
        max_value = np.max(max_vals)
    except ValueError:
        max_value = np.nan
    result = (min_value, max_value, sum(sum_vals), sum(count_vals))
    return result

def _reduce_stats(graph_inputs, input_params):
    ''' Compute min, max, sum, and count of all data'''
    try:
        data_min = min(0.0, np.min([input[0] for input in graph_inputs]))
    except ValueError:
        data_min = 0.0
    try:
        data_max = max(0.0, np.max([input[1] for input in graph_inputs]))
    except ValueError:
        data_max = 0.0
    data_sum = sum([input[2] for input in graph_inputs])
    data_count = sum([input[3] for input in graph_inputs])
    return (data_min, data_max, data_sum, data_count)

def _map_variance(input_params):
    ''' Return sum, count, of (xda - mean) squared '''
    mean = input_params['mean']
    vis_axis = input_params['vis_axis']
    vis_data = input_params['vis_data']

    sq_diff_sum = 0.0
    sq_diff_count = 0

    ps_iter = processing_set_iterator(
        input_params['data_selection'],
        input_params['input_data_store'],
        input_params['input_data'],
        data_variables=[vis_data, 'FLAG'],
        load_sub_datasets=False
    )

    for xds in ps_iter:
        xda = _get_stats_xda(xds, vis_axis)
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

def _map_min(input_params):
    ''' Return minimum value of input coord '''
    coord = input_params['coord']
    min_vals = []

    ps_iter = processing_set_iterator(
        input_params['data_selection'],
        input_params['input_data_store'],
        input_params['input_data'],
        data_variables=[coord],
        load_sub_datasets=False
    )
 
    for xds in ps_iter:
        xda = xds[coord]
        min_val = np.min(xda).values.item()
        min_vals.append(min_val)
    return min(min_vals)

def _reduce_min(graph_inputs, input_params):
    ''' Compute min of all data (scalar) '''
    return min(graph_inputs)
