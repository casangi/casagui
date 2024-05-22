import multiprocessing

from xradio.vis.load_processing_set import processing_set_iterator
from graphviper.graph_tools import generate_dask_workflow
from graphviper.graph_tools.coordinate_utils import make_parallel_coord, interpolate_data_coords_onto_parallel_coords
from graphviper.graph_tools.map import map
from graphviper.graph_tools.reduce import reduce

import dask
import numpy as np

def _get_stats_xda(xds, data_var):
    ''' Return xda with only unflagged cross-corr visibility data '''
    xda = np.absolute(xds[data_var]) # complex64 to float32
    unflagged_xda = xda.where(np.logical_not(xds.FLAG), drop=True)
    stats_xda = unflagged_xda.where(
        xds.baseline_antenna1_id != xds.baseline_antenna2_id,
        drop=True
    )
    if stats_xda.size == 0:
        stats_xda = unflagged_xda
    return stats_xda

def _map_stats(input_params):
    ''' Return min, max, sum, and count of data chunk '''
    vis_data_var = input_params['vis_data_var']

    min_val = max_val = sum_val = 0.0
    count = 0

    ps_iter = processing_set_iterator(
        input_params['data_selection'],
        input_params['input_data_store'],
        data_variables=[vis_data_var, 'FLAG'],
        load_sub_datasets=False
    )

    for xds in ps_iter:
        xda = _get_stats_xda(xds, vis_data_var)
        if xda.size > 0:
            min_val = min(min_val, np.nanmin(xda))
            max_val = max(max_val, np.nanmax(xda))
            sum_val += np.nansum(xda)
            count += xda.count().values
    return (min_val, max_val, sum_val, count)

def _reduce_stats(graph_inputs, input_params):
    ''' Compute min, max, sum, and count of all data'''
    data_min = min(0.0, min([input[0] for input in graph_inputs]))
    data_max = max(0.0, max([input[1] for input in graph_inputs]))
    data_sum = sum([input[2] for input in graph_inputs])
    data_count = sum([input[3] for input in graph_inputs])
    return (data_min, data_max, data_sum, data_count)

def _map_variance(input_params):
    ''' Return sum, count, of (xda - mean) squared '''
    mean = input_params['mean']
    vis_data_var = input_params['vis_data_var']

    sq_diff_sum = 0.0
    sq_diff_count = 0

    ps_iter = processing_set_iterator(
        input_params['data_selection'],
        input_params['input_data_store'],
        data_variables=[vis_data_var, 'FLAG'],
        load_sub_datasets=False
    )

    for xds in ps_iter:
        xda = _get_stats_xda(xds, vis_data_var)
        if xda.size > 0:
            sq_diff = (xda - mean) ** 2
            sq_diff_sum += np.sum(sq_diff).values
            sq_diff_count += sq_diff.count().values
    return (sq_diff_sum, sq_diff_count)
 
def _reduce_variance(graph_inputs, input_params):
    ''' Compute sum and count of all (xda-mean) squared data'''
    sq_diff_sum = sum([input[0] for input in graph_inputs])
    sq_diff_count = sum([input[1] for input in graph_inputs])
    return (sq_diff_sum, sq_diff_count)

def calculate_vis_stats(ps, ps_store, vis_type):
    '''
        Calculate stats for unflagged visibilities: min, max, mean, std
        ps (msv4 processing set): visibility data with flags
        ps_store (str): path to visibility file
        vis_type (str): type of visibility ('data' or 'corrected')
    '''
    vis_data_var = 'VISIBILITY' if vis_type=='data' else 'VISIBILITY_CORRECTED'
    input_params = {'input_data_store': ps_store}
    input_params['vis_data_var'] = vis_data_var
    n_chunks = 8

    # Calculate min, max, mean across each ddi using frequency parallel coords
    data_min = None
    data_max = None
    data_sum = 0.0
    data_count = 0
    for key in ps:
        frequencies = ps[key].frequency
        parallel_coords = {"frequency": make_parallel_coord(coord=frequencies, n_chunks=n_chunks)}
        node_task_data_mapping = interpolate_data_coords_onto_parallel_coords(parallel_coords, input_data=ps)

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
        results = dask.compute(dask_graph)
        ddi_min, ddi_max, ddi_sum, ddi_count = results[0]
        data_min = min(data_min, ddi_min) if data_min is not None else ddi_min
        data_max = max(data_max, ddi_max) if data_max is not None else ddi_max
        data_sum += ddi_sum
        data_count += ddi_count

    data_mean = data_sum / data_count
    #print(f"stats: min={data_min}, max={data_max}, mean={data_mean}")
    input_params['mean'] = data_mean

    # Calculate variance and standard deviation
    var_sum = 0.0
    var_count = 0
    for key in ps:
        frequencies = ps[key].frequency
        parallel_coords = {"frequency": make_parallel_coord(coord=frequencies, n_chunks=n_chunks)}
        node_task_data_mapping = interpolate_data_coords_onto_parallel_coords(parallel_coords, input_data=ps)

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
        ddi_var_sum, ddi_var_count = results[0]
        var_sum += ddi_var_sum
        var_count += ddi_var_count

    data_variance = var_sum / var_count
    data_stddev = data_variance ** 0.5
    #print(f"stats: variance={data_variance}, stddev={data_stddev}")
    return (data_min, data_max, data_mean, data_stddev)
