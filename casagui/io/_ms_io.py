"""
Functions for reading MSv2 or zarr MSv4 into xradio ProcessingSet
"""

import os.path

from xradio.measurement_set.open_processing_set import open_processing_set

try:
    # requires python-casacore
    from xradio.measurement_set.convert_msv2_to_processing_set import convert_msv2_to_processing_set
    __have_xradio = True
except:
    __have_xradio = False

def get_processing_set(ms_path, logger):
    '''
    Read msv2 or zarr file into processing set

    Args:
        ms_path (str): path to MSv2 or MSv4 zarr file
    Returns:
        xradio ProcessingSet
    '''

    if not os.path.exists(ms_path):
        raise RuntimeError(f"Visibility file {ms_path} does not exist")

    # Remove trailing / or entire path is basename with no extension
    if ms_path[-1] == '/':
        ms_path = ms_path[:-1]

    basename, ext = os.path.splitext(ms_path)
    if ext == ".zarr":
        zarr_path = ms_path
    else:
        if not __have_xradio:
            raise RuntimeError("Cannot import xradio module to convert MeasurementSet v2")
        zarr_path = basename + ".ms.zarr"
        if not os.path.exists(zarr_path):
            print(f"Converting input MS {ms_path} to zarr {zarr_path}")
            convert_msv2_to_processing_set(
                in_file=ms_path,
                out_file=zarr_path
                )

    if not os.path.exists(zarr_path):
        raise RuntimeError("Zarr file does not exist")

    ps = open_processing_set(zarr_path)
    if not ps or len(ps) == 0:
        raise RuntimeError("Failed to read measurement set into processing set.")
    logger.info(f"Processing set contains {len(ps)} msv4 datasets.")

    return ps, zarr_path
