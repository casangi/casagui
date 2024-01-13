import math
import os.path
from psutil import cpu_count, virtual_memory
import sys
import time

from xradio.vis.convert_msv2_to_processing_set import convert_msv2_to_processing_set
from xradio.vis.read_processing_set import read_processing_set

from bokeh.models.formatters import DatetimeTickFormatter
import dask
import dask.dataframe as dd
from dask.diagnostics import ProgressBar, Profiler, ResourceProfiler, CacheProfiler, visualize
import datashader as ds
import datashader.transfer_functions as tf 
import holoviews as hv
import holoviews.operation.datashader
import hvplot.dask
import matplotlib.pyplot as plt
from numpy import absolute as np_abs
from pandas import to_datetime

def vis_to_ps(vis_path):
    '''
    read_vis: read visibilities in vis_path. If ms, convert to zarr if does not exist.
    input vis_path(str): path to input .ms or .zarr file
    returns (xarray Dataset): xradio processing set
    '''
    ms_name = vis_path
    basename, ext = os.path.splitext(vis_path)
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
        raise RuntimeError("No .zarr file for visibilities")
    return read_processing_set(zarr_name)

def xds_to_ddf(xds):
    '''
    xds_to_partitioned_frame: read dataset into dask dataframe
    input xds (xarray Dataset): msv4 in processing set
    returns: list of dask DataFrames with amplitude and time columns, partitioned by time selection and correlation
    '''
    ddfs = []
    npoints = 0
    nrows = xds.dims['time'] * xds.dims['baseline_id']
    ncorr = xds.dims['polarization']

    # Partition xds if >5000 rows
    increment = xds.dims['time']
    npartitions = 1
    if nrows > 5000:
        npartitions = math.ceil(nrows / 5000);
        increment = math.ceil(xds.dims['time'] / npartitions)
    #print(f"create {npartitions * ncorr} partitions ({increment} times and 1 correlation each) from {nrows} rows")

    for i in range(0, xds.dims['time'], increment):
        xds_part = xds.isel(time=slice(i, i + increment))
        for j in range(ncorr):
            xds_corr = xds_part.isel(polarization=j)
            xda = np_abs(xds_corr.VISIBILITY).rename('amp')
            xda['time'] = to_datetime(xda.time, unit='s').astype('int64')/10**6
            npoints += xda.size
            # only keep amp and time for ddf conversion
            xda = xda.drop([coord for coord in xda.coords if coord != 'time'])
            ddf = xda.to_dataset().to_dask_dataframe()[['time', 'amp']]
            ddfs.append(ddf)
    return ddfs, npoints

def create_image(ddf, xaxis, yaxis):
    ''' Create datashader Image from dask Dataframe '''
    canvas = ds.Canvas(900, 600)
    # canvas.points runs dask.compute
    start = time.time()
    #with ProgressBar():
    #with Profiler() as prof, ResourceProfiler() as rprof, CacheProfiler() as cprof:
    raster = canvas.points(ddf, xaxis, yaxis, agg=ds.count())
    print(f"loading points time {(time.time() - start):.3f}s")
    #visualize([prof, rprof, cprof])
    img = tf.shade(raster)
    return img

def create_plot(img, xaxis, yaxis):
    time_formatter = DatetimeTickFormatter(microseconds='%H:%M %3fus',
        milliseconds='%S.%3Ns',
        seconds='%H:%M:%S',
        minsec='%H:%M:%S',
        hours='%H:%M:%S',
        days='%F')
    plot = hv.RGB(hv.operation.datashader.shade.uint32_to_uint8_xr(img)).opts(
            xformatter=time_formatter,
            xlabel=xaxis.capitalize(),
            ylabel=yaxis.capitalize(),
            title=yaxis.capitalize() + " vs. " + xaxis.capitalize(),
            width=900,
            height=600
        )
    return plot

def main(argv):
    '''
        Create an amplitude vs. time scatter plot for visibilities in a .zarr or .ms file
        To run: python3 vis_scatter.py /path/to/ms
    '''
    if len(argv) < 1:
        raise RuntimeError("Input a .zarr or .ms path")

    vis_path = argv[0]
    if not os.path.exists(vis_path):
        raise RuntimeError("Input path does not exist")

    # resources info
    print(f"Number of cores: {cpu_count()}")
    total_mem_GB = virtual_memory().total / 2**30
    available_mem_GB = virtual_memory().available / 2**30
    print(f"Total memory: {total_mem_GB:.2f} GB, available memory: {available_mem_GB:.2f} GB")

    # Read ms->zarr file into xradio processing set
    start = time.time()
    ps = vis_to_ps(vis_path)
    if len(ps.keys()) == 0:
        raise RuntimeError("Input .zarr file could not be read into a processing set")
    print(f"Processing {len(ps.keys())} msv4 datasets")

    # Load data into a single combined dask dataframe so dask can manage compute
    start_ddf = time.time()
    num_points = 0
    combined_ddf = []
    for key in ps.keys():
        print(f"Reading dataset {key}")
        ddfs, ddf_npoints = xds_to_ddf(ps[key])
        num_points += ddf_npoints
        combined_ddf.extend(ddfs)
    combined_ddf = dd.concat(combined_ddf)
    print(f"ps to ddf time {(time.time() - start_ddf):.3f}s, ddf partitions: {combined_ddf.npartitions}")
    # chunksize is nan due to dask.delayed, so have to compute
    #print(f"ddf compute chunksizes: {combined_ddf.values.compute_chunk_sizes()}")

    # Create datashader image then plot
    print(f"Plotting {num_points:.3e} points")
    img = create_image(combined_ddf, "time", "amp")
    plot = create_plot(img, "time", "amp")

    # Save plot in current directory
    filename = os.path.splitext(os.path.basename(vis_path))[0] + ".png"
    print(f"Saving plot to {filename}")
    hvplot.save(plot, filename)

    print(f"total time {(time.time() - start):.3f}s")

if __name__ == "__main__":
    main(sys.argv[1:])
