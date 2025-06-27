import os
import ssl
import certifi
import urllib
import tarfile
import time

from toolviper.dask.client import local_client

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
## where to save plots
##
plot_dir = "demo_plots"

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


def plot_ms_waterfall():
    ''' Show MsRaster features '''
    # Download test ms
    fetch_ms()

    # Create plot directory
    if not os.path.exists(plot_dir):
        os.mkdir(plot_dir)

    # Start toolviper dask client
    client = local_client()

    # Converts ms to zarr, and gets xradio ProcessingSet.
    # logging levels are 'debug', 'info' , 'warning', 'error', 'critical'
    msr = MsRaster(ms_path, log_level='info', show_gui=False)

    # ProcessingSet selection using summary column name and value, or MeasurementSetXds coordinates.
    # For selection options: msr.summary()
    msr.select_ps(intents='OBSERVE_TARGET#ON_SOURCE')
    msr.select_ms(antenna1='DA42_A050')

    # Demo waterfall plots with baseline iteration
    msr.plot(x_axis='frequency', iter_axis='baseline', iter_range=(0, 5), subplots=(2, 3), color_mode=None)
    msr.show()
    filename=os.path.join(plot_dir, "waterfall_plots.png")
    msr.save(filename)

if __name__ == '__main__':
    plot_ms_waterfall()
