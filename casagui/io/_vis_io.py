"""
Functions for reading visibilities (MSv2 or zarr MSv4) into processing set
"""

import os.path

try:
    from xradio.vis.read_processing_set import read_processing_set
    # requires python-casacore
    from xradio.vis.convert_msv2_to_processing_set import convert_msv2_to_processing_set
    __have_xradio = True
except:
    __have_xradio = False

def get_processing_set(vis_path):
    '''
    Read msv2 or zarr file into processing set

    Args:
        vis_path (str): path to .ms or .vis.zarr file
    Returns:
        xradio processing set (xarray Dataset)
    '''

    if not os.path.exists(vis_path):
        raise RuntimeError(f"Visibility file {vis_path} does not exist")

    # Remove trailing / or entire path is basename with no extension
    if vis_path[-1] == '/':
        vis_path = vis_path[:-1]

    basename, ext = os.path.splitext(vis_path)
    if ext == ".zarr":
        zarr_path = vis_path
    else:
        if not __have_xradio:
            raise RuntimeError("Cannot import xradio module to read MeasurementSet")
        zarr_path = basename + ".vis.zarr"
        if not os.path.exists(zarr_path):
            print(f"Converting input MS {vis_path} to zarr {zarr_path}")
            convert_msv2_to_processing_set(
                in_file=vis_path,
                out_file=zarr_path,
                partition_scheme="ddi_intent_field"
            )

    if not os.path.exists(zarr_path):
        raise RuntimeError("Zarr file does not exist")
    return read_processing_set(zarr_path), zarr_path
