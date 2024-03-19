import math
import os.path
from psutil import cpu_count, virtual_memory
import sys
import time

from xradio.vis.convert_msv2_to_processing_set import convert_msv2_to_processing_set
from xradio.vis.read_processing_set import read_processing_set
from xradio.vis import load_vis_block
from graphviper.graph_tools.map import map
from graphviper.graph_tools.reduce import reduce
from graphviper.graph_tools.coordinate_utils import make_parallel_coord, interpolate_data_coords_onto_parallel_coords

import dask
import numpy as np
#import xarray as xr

def vis_to_ps(vis_path):
    '''
    vis_to_ps: read visibilities in vis_path to xradio processing set.
    If ms, convert to zarr if does not exist.

    input vis_path(str): path to input .ms or .zarr file
    returns (xarray Dataset): xradio processing set
    '''
    basename, ext = os.path.splitext(vis_path)
    if ext == ".zarr":
        zarr_name = vis_path
    else:
        zarr_name = basename + ".vis.zarr"
        if not os.path.exists(zarr_name):
            print("Converting input MS", vis_path, "to", zarr_name)
            start_convert = time.time()
            convert_msv2_to_processing_set(
                in_file=vis_path,
                out_file=zarr_name,
                partition_scheme="ddi_intent_field"
            )
            print("convert to zarr took", time.time() - start_convert)
        if not os.path.exists(zarr_name):
            raise RuntimeError("Conversion to .zarr failed")
    return read_processing_set(zarr_name), zarr_name

def get_stats_xda(xds):
    # use only unflagged cross-corr data
    xda = np.absolute(xds.VISIBILITY) # complex64 to float32
    unflagged_xda = xda.where(np.logical_not(xds.FLAG))
    stats_xda = unflagged_xda.where(
        xds.baseline_antenna1_id != xds.baseline_antenna2_id,
        drop=True
    )
    if stats_xda.size == 0:
        stats_xda = unflagged_xda
    return stats_xda

def map_stats(input_params):
    ''' Return min, max, sum, and count of data chunk '''
    min_val = max_val = sum_val = 0.0
    count = 0

    for key in input_params['data_selection']:
        # change dict key 'frequency' -> 'freq'
        block_des = {'freq': input_params['data_selection'][key]}

        xds = load_vis_block(
            infile=os.path.join(input_params['input_data_store'], key),
            block_des=block_des,
            partition_key=(None, None, None) #what is this
        )
        xda = get_stats_xda(xds)
        if xda.size > 0:
            min_val = min(min_val, np.nanmin(xda))
            max_val = max(max_val, np.nanmax(xda))
            sum_val += np.nansum(xda)
            count += xda.count().values
    return (min_val, max_val, sum_val, count)

def reduce_stats(graph_inputs, input_params):
    ''' Compute min, max, sum, and count of all data'''
    data_min = min(0.0, min([input[0] for input in graph_inputs]))
    data_max = max(0.0, max([input[1] for input in graph_inputs]))
    data_sum = sum([input[2] for input in graph_inputs])
    data_count = sum([input[3] for input in graph_inputs])
    data_mean = data_sum / data_count
    return (data_min, data_max, data_mean)

def map_variance(input_params):
    ''' Return sum, count, of (xda-mean) squared '''
    sq_diff_sum = 0.0
    sq_diff_count = 0
    mean = input_params['mean']

    for key in input_params['data_selection']:
        # change dict key 'frequency' -> 'freq'
        block_des = {'freq': input_params['data_selection'][key]}

        xds = load_vis_block(
            infile=os.path.join(input_params['input_data_store'], key),
            block_des = block_des,
            partition_key=(None, None, None) #what is this
        )
        xda = get_stats_xda(xds)
        if xda.size > 0:
            sq_diff = (xda - mean) ** 2
            sq_diff_sum += np.sum(sq_diff).values
            sq_diff_count += sq_diff.count().values
    return (sq_diff_sum, sq_diff_count)
 
def reduce_variance(graph_inputs, input_params):
    ''' Compute sum and count of all (xda-mean) squared data'''
    sq_diff_sum = sum([input[0] for input in graph_inputs])
    sq_diff_count = sum([input[1] for input in graph_inputs])
    return (sq_diff_sum / sq_diff_count)

def main(argv):
    '''
        Calculate basic stats for visibilities in a single ddi
        To run: python3 ddi_stats.py /path/to/vis [ddi]

        vis (str): ms or zarr filename
        ddi (int): [optional] use first ddi if not specified
    '''
    if len(argv) < 1:
        raise RuntimeError("Input a .zarr or .ms path")

    vis_path = argv[0]
    if not os.path.exists(vis_path):
        raise RuntimeError("Input path does not exist")

    ddi = None 
    if len(argv) > 1:
        ddi = int(argv[1])

    # resources info
    print(f"Number of cores: {cpu_count()}")
    total_mem_GB = virtual_memory().total / 2**30
    available_mem_GB = virtual_memory().available / 2**30
    print(f"Total memory: {total_mem_GB:.2f} GB, available memory: {available_mem_GB:.2f} GB")

    # Read ms->zarr file into xradio processing set
    ps, zarr_name = vis_to_ps(vis_path)

    ddi_list = sorted(set(ps.summary()['ddi']))
    if ddi == None:
        ddi = ddi_list[0]
        print(f"No ddi selected, using first ddi {ddi}")
    elif ddi not in ddi_list:
        raise ValueError(f"Invalid ddi selection {ddi}. Please select from {ddi_list}")

    # Processing set for one ddi
    ddi_ps = {}
    for key in ps.keys():
        xds = ps[key]
        if xds.ddi != ddi:
            continue
        print(f"Reading dataset {key}")
        print("dataset shape:", xds.VISIBILITY.shape)
        ddi_ps[key] = xds
    print(f"Processing {len(ddi_ps.keys())} msv4 datasets")

    # Calculate min, max, mean across all ddi data
    frequencies = list(ddi_ps.values())[0].frequency.to_dict()
    n_chunks = 16 
    parallel_coords = {"frequency": make_parallel_coord(coord=frequencies, n_chunks=n_chunks)}
    node_task_data_mapping = interpolate_data_coords_onto_parallel_coords(parallel_coords, input_data=ddi_ps)
    input_params = {'input_data_store': zarr_name}

    start = time.time()
    graph = map(
        input_data=ddi_ps,
        node_task_data_mapping=node_task_data_mapping,
        node_task=map_stats,
        input_params=input_params
    )
    graph_reduce = reduce(
        graph, reduce_stats, input_params, mode='single_node'
    )
    results = dask.compute(graph_reduce)
    data_min, data_max, data_mean = results[0][0]
    print(f"stats: min={data_min}, max={data_max}, mean={data_mean}")

    # Calculate variance and standard deviation
    input_params['mean'] = data_mean
    graph = map(
        input_data=ps,
        node_task_data_mapping=node_task_data_mapping,
        node_task=map_variance,
        input_params=input_params
    )
    graph_reduce = reduce(
         graph, reduce_variance, input_params, mode='single_node'
    )
    stats = dask.compute(graph_reduce)
    variance = stats[0][0]
    stddev = variance ** 0.5
    print(f"stats: variance={variance}, stddev={stddev}")

    clipmin = max(data_min, data_mean - (3.0 * stddev))
    clipmax = min(data_max, data_mean + (3.0 * stddev))
    print(f"Use colorbar limits {clipmin} to {clipmax}")
    print(f"total time {(time.time() - start):.3f}s")

if __name__ == "__main__":
    main(sys.argv[1:])
