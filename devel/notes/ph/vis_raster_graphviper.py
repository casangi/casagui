import math
import os.path
from psutil import cpu_count, virtual_memory
import sys
import time

from xradio.vis.convert_msv2_to_processing_set import convert_msv2_to_processing_set
from xradio.vis.read_processing_set import read_processing_set
from graphviper.graph_tools.map import map
from graphviper.graph_tools.reduce import reduce
from graphviper.graph_tools.coordinate_utils import make_parallel_coord, interpolate_data_coords_onto_parallel_coords

import dask
#from dask.diagnostics import Profiler, ResourceProfiler, CacheProfiler, visualize
import holoviews as hv
import hvplot.xarray
import numpy as np
from pandas import to_datetime
import xarray as xr

def vis_to_ps(vis_path):
    '''
    read_vis: read visibilities in vis_path. If ms, convert to zarr if does not exist.
    input vis_path(str): path to input .ms or .zarr file
    returns (xarray Dataset): xradio processing set
    '''
    basename, ext = os.path.splitext(vis_path)
    if ext == ".zarr":
        zarr_name = vis_path
    else:
        ms_name = vis_path
        zarr_name = basename + ".vis.zarr"
        if not os.path.exists(zarr_name):
            print("Converting input MS", ms_name, "to", zarr_name)
            start_convert = time.time()
            convert_msv2_to_processing_set(
                in_file=ms_name,
                out_file=zarr_name,
                partition_scheme="ddi_intent_field"
            )
            print("convert to zarr took", time.time() - start_convert)
        if not os.path.exists(zarr_name):
            raise RuntimeError("Conversion to .zarr failed")
    return read_processing_set(zarr_name), os.path.basename(basename)

def get_baseline_pairs(n_antennas):
    ''' Return a dict {id: (ant1, ant2)} to standardize baseline ids '''
    baselines = []
    for i in range(n_antennas):
        for j in range(i, n_antennas):
            baselines.append((i, j))
    return baselines

def get_antenna_info(antenna_xds):
    names = antenna_xds.name.values
    stations = antenna_xds.station.values
    antenna_names = [f"{names[i]}@{stations[i]}" for i in range(len(names))]
    baselines = get_baseline_pairs(len(antenna_names))
    return antenna_names, baselines

def set_baseline_ids(xds, baselines):
    ''' Set baseline ids coordinate in xda according to each ant1&ant2 pair '''
    ant1 = xds.baseline_antenna1_id.values
    ant2 = xds.baseline_antenna2_id.values
    new_baseline_ids = []
    for idx in xds.baseline_id.values:
        try:
            new_id = baselines.index((ant1[idx], ant2[idx]))
        except ValueError:
            new_id = np.nan
        new_baseline_ids.append(new_id)
    xds["baseline_id"] = np.array(new_baseline_ids)

def get_time_ticks(time_xda):
    ''' Return list of (index, time string) '''
    date = to_datetime(time_xda.values[0], unit='s').strftime("%d-%b-%Y")
    times = to_datetime(time_xda, unit='s').strftime("%H:%M:%S")
    time_ticks = list(enumerate(times.values))
    return date, time_ticks

def get_baseline_ticks(xda, baselines, ant_names):
    ''' Return list of (index, ant1 name) when ant1 changes in baseline '''
    baseline_ticks = []
    baseline_ids = xda.baseline_id.values # values are index into baselines
    tick_ant1 = None
    tick_idx = None
    tick_increment = len(ant_names) / 3 

    # Add label for every new ant1 if there is room (increment)
    for idx, baseline_id in enumerate(baseline_ids):
        ant1, ant2 = baselines[baseline_id]
        if ant1 != tick_ant1:
            tick_ant1 = ant1
            if tick_idx is None:
                baseline_ticks.append((idx, ant_names[ant1]))
                tick_idx = idx
            else:
                if (idx - tick_idx) >= tick_increment:
                    baseline_ticks.append((idx, ant_names[ant1]))
                    tick_idx = idx
    return baseline_ticks

def map_stats(input_params):
    ''' Return min, max, sum, and count of data chunk '''
    #print("map_stats input params", input_params)
    min_val = max_val = sum_val = 0.0
    count = 0

    for key in input_params['data_selection']:
        xds = input_params['vis'][key].isel(input_params['data_selection'][key])
        xda = xds.VISIBILITY
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
    return (data_min, data_max, data_sum, data_count)
   
def map_sq_diff(input_params):
    ''' Return sum, count, of (xda-mean) squared '''
    #print("map_sq_diff input params", input_params)
    sq_diff_sum = 0.0
    sq_diff_count = 0
    mean = input_params['mean']

    for key in input_params['data_selection']:
        xds = input_params['vis'][key].isel(input_params['data_selection'][key])
        xda = xds.VISIBILITY

        sq_diff = (xda - mean) ** 2
        sq_diff_sum += np.sum(sq_diff).values
        sq_diff_count += sq_diff.count().values
    return (sq_diff_sum, sq_diff_count)
 
def reduce_sq_diff(graph_inputs, input_params):
    ''' Compute sum and count of all (xda-mean) squared data'''
    sq_diff_sum = sum([input[0] for input in graph_inputs])
    sq_diff_count = sum([input[1] for input in graph_inputs])
    return (sq_diff_sum, sq_diff_count)

def calc_color_limits(ps):
    ''' Clip data color scaling ranges to 3-sigma limits as in msview '''
    data_min = data_max = data_sum = 0.0
    data_count = 0

    first_key = list(ps.keys())[0]
    frequencies = ps[first_key].frequency.to_dict()
    parallel_coords = {"frequency": make_parallel_coord(coord=frequencies, n_chunks=8)}
    node_task_data_mapping = interpolate_data_coords_onto_parallel_coords(parallel_coords, input_data=ps)

    input_params = {'vis': ps}
    graph = map(
        input_data=ps,
        node_task_data_mapping=node_task_data_mapping,
        node_task=map_stats,
        input_params=input_params
    )
    graph_reduce = reduce(
        graph, reduce_stats, input_params, mode='single_node'
    )
    stats = dask.compute(graph_reduce)
    data_min, data_max, data_sum, data_count = stats[0][0]

    mean = data_sum / data_count
    input_params['mean'] = mean
    graph = map(
        input_data=ps,
        node_task_data_mapping=node_task_data_mapping,
        node_task=map_sq_diff,
        input_params=input_params
    )
    graph_reduce = reduce(
         graph, reduce_sq_diff, input_params, mode='single_node'
    )
    stats = dask.compute(graph_reduce)
    sq_diff_sum, sq_diff_count = stats[0][0]

    variance = sq_diff_sum / sq_diff_count
    stddev = variance ** 0.5
    clipmin = max(data_min, mean - (3.0 * stddev))
    clipmax = min(data_max, mean + (3.0 * stddev))
    return (clipmin, clipmax)

def create_plot(xda, vis_name, ddi, date, color_limits, x_ticks, y_ticks, is_flagged = False):
    # create holoviews.element.raster.Image
    title = f"{vis_name}\nddi={ddi}  frequency={xda.frequency.values:.3f} {xda.frequency.units}  correlation={xda.polarization.values}"
    xlabel = "Baseline Antenna1"
    ylabel = f"Time ({date})"
    y_tick_inc = int(len(y_ticks) / 10)

    colormap = "Viridis" # "Plasma" "Magma"
    clabel = f"{xda.name} ({xda.attrs['units']})"
    cb_position = "left"
    if is_flagged:
        colormap = "kr" # black to reds, "kb" blues
        clabel = f"flagged {xda.name} ({xda.attrs['units']})"
        cb_position = "right"
        color_limits = None

    return xda.hvplot(x="baseline_id", y="time", width=900, height=600,
        clim=color_limits, cmap=colormap, clabel=clabel,
        title=title, xlabel=xlabel, ylabel=ylabel,
        rot=90, xticks=x_ticks, yticks=y_ticks[::y_tick_inc]
    ).opts(colorbar_position=cb_position)

def main(argv):
    '''
        Create a time vs. baseline raster plot for visibilities in a .zarr or .ms file
        To run: python3 vis_raster.py /path/to/vis [ddi]

        vis: ms or zarr
        ddi: use first if not specified
    '''
    if len(argv) < 1:
        raise RuntimeError("Input a .zarr or .ms path")

    vis_path = argv[0]
    xaxis = 'baseline_id'
    yaxis = 'time'
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
    start = time.time()
    ps, vis_basename = vis_to_ps(vis_path)
    print(f"Processing {len(ps.keys())} msv4 datasets")

    ddi_list = sorted(set(ps.summary()['ddi']))
    if ddi == None:
        ddi = ddi_list[0]
        print(f"No ddi selected, using first ddi {ddi}")
    elif ddi not in ddi_list:
        raise ValueError(f"Invalid ddi selection {ddi}. Please select from {ddi_list}")

    # Antenna names (name@station) and baseline pairs [(ant1, ant2)]
    antenna_names, baselines = get_antenna_info(ps[list(ps.keys())[0]].antenna_xds)

    xds_list = []
    limits_ps = {}
    for key in ps.keys():
        xds = ps[key]
        if xds.ddi != ddi:
            continue
        print(f"Reading dataset {key}")
        print("vis shape", xds.VISIBILITY.shape)
        # set consistent baseline ids across xds for concat
        set_baseline_ids(xds, baselines)
        # get amplitude of visibilities
        xds["VISIBILITY"] = np.absolute(xds.VISIBILITY)
        xds_list.append(xds)

        # use only unflagged cross-corr visibility data
        limits_xds = xds
        unflagged_xda = xds.VISIBILITY.where(np.logical_not(xds.FLAG), drop=True)
        xda = unflagged_xda.where(
            unflagged_xda.baseline_antenna1_id != unflagged_xda.baseline_antenna2_id,
            drop=True
        )
        if xda.size == 0: # no cross-corr baselines
            xda = unflagged_xda
        limits_xds['VISIBILITY'] = xda
        limits_ps[key] = limits_xds

    # Find colorbar limits across all ddi data
    color_limits = calc_color_limits(limits_ps)
    print(f"Clipping unflagged data colorbar at ({color_limits[0]}, {color_limits[1]})")

    # Concat xds and set amp, freq
    plot_xds = xr.concat(xds_list, dim='time')

    # Select first channel and pol
    plot_xds = plot_xds.isel(frequency=0, polarization=0)
    plot_xds['frequency'] = plot_xds.frequency / 1.0e9;
    plot_xds['frequency'] = plot_xds.frequency.assign_attrs(units="GHz");

    # Sort by time to assign time index and labels in order
    plot_xds.sortby('time')

    # Data arrays needed for plot
    amp_xda = plot_xds.VISIBILITY
    flag_xda = plot_xds.FLAG

    # Set time index 0-ntimes for regularly-spaced axis
    date, time_ticks = get_time_ticks(amp_xda.time)
    amp_xda['time'] = np.array(range(len(amp_xda.time)))
    flag_xda['time'] = amp_xda.time
    # Set baseline index 0-nbaselines
    baseline_ticks = get_baseline_ticks(amp_xda.baseline_id, baselines, antenna_names)
    amp_xda['baseline_id'] = np.array(range(len(amp_xda.baseline_id)))
    flag_xda['baseline_id'] = amp_xda.baseline_id

    layout = None # holds unflagged data overplotted with flagged data

    # Plot unflagged data
    amp_unflagged = amp_xda.where(flag_xda == False).rename('amp').assign_attrs(units="Jy")
    plot1 = create_plot(amp_unflagged, vis_basename, ddi, date, color_limits, baseline_ticks, time_ticks)
    layout = plot1

    # Plot flagged data with different colormap
    amp_flagged = amp_xda.where(flag_xda == True).rename('amp').assign_attrs(units="Jy")
    plot2 = create_plot(amp_flagged, vis_basename, ddi, date, color_limits, baseline_ticks, time_ticks, True)
    layout = layout * plot2 if layout is not None else plot2

    # Combine plots and save in current directory
    if layout is None:
        print(f"Plot failed")
    else:
        filename = f"{vis_basename}_ddi_{ddi}_raster.png"
        print(f"Saving plot to {filename}")
        hvplot.save(layout, filename)
    print(f"Elapsed time {(time.time() - start):.3f}s")

if __name__ == "__main__":
    main(sys.argv[1:])
