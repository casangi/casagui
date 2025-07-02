import os
import ssl
import certifi
import urllib
import tarfile

from casagui.apps import MsRaster

##
## demo measurement set to use
##
ms_path = 'sis14_twhya_selfcal.ms'
##
## where to fetch the demo measurement set
##
ms_url = "https://casa.nrao.edu/download/devel/casavis/data/sis14_twhya_selfcal.ms.tar.gz"
##

def fetch_ms():
    if not os.path.isdir(ms_path):
        try:
            context = ssl.create_default_context(cafile=certifi.where())
            tstream = urllib.request.urlopen(ms_url, context=context, timeout=400)
            tar = tarfile.open(fileobj=tstream, mode="r:gz")
            tar.extractall( )
        except urllib.error.URLError:
            print("Failed to open connection to "+ms_url)
            raise

    if not os.path.isdir(ms_path):
        raise  RuntimeError("Failed to fetch measurement set")

def show_ms_plot_features():
    ''' Show features of base class common to MsRaster and MsScatter '''
    # Download test ms
    fetch_ms()

    # __init__ sets ms_path, log_level, interactive
    # Converts ms to zarr and sets xradio ProcessingSet
    # Could also use MsScatter
    msr = MsRaster(ms_path)

    # Demo xradio ProcessingSet functions
    # Default summary data group is 'base'
    msr.summary(data_group='base') # print pandas dataframe, used for ps selection
    print("\n----- summary columns [spw_name, start_frequency, end_frequency]:")
    msr.summary(columns=['spw_name', 'start_frequency', 'end_frequency']) # select subset (str or list) of summary columns
    print("\n----- summary by_ms:")
    msr.summary(columns='by_ms') # organizes summary info by each MSv4 xarray Datasets

    # Get list of data/flag/weight/uvw group names
    print("data groups:\n", msr.data_groups())

    # Get list of unique values for dimensions
    for dim in ['time', 'baseline', 'antenna1', 'antenna2', 'frequency', 'polarization']:
        print("-----", dim, "dimension:")
        print(msr.get_dimension_values(dim))

    # ProcessingSet plots
    # Plot antenna positions and label antenna names (default False).
    msr.plot_antennas(label_antennas=False)
    msr.plot_antennas(label_antennas=True)

    # Plot phase centers and show field names for data group (default False)
    # The field and source xds is an attribute of the correlated_data in the data group.
    msr.plot_phase_centers(label_fields=False, data_group='base')
    msr.plot_phase_centers(label_fields=True, data_group='base')

if __name__ == '__main__':
    show_ms_plot_features()
